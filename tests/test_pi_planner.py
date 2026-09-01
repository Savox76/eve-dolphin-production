from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from eve_dolphin.characters import CharacterRepository, EveCharacter
from eve_dolphin.database import Database
from eve_dolphin.pi import (
    PiCatalog,
    PiCatalogRepository,
    PiCommodity,
    PiGoalMode,
    PiOperationMode,
    PiPlanLine,
    PiPlannerService,
    PiPlanRequest,
    PiPlanResult,
    PiProfile,
    PiProfileRepository,
    PiRecipe,
    PiRecipeItem,
    PiStorageStrategy,
    PiTier,
    PlanetaryOverviewService,
    SavedPiPlan,
    SavedPiPlanRepository,
    SpaceKind,
    forecast_colony,
)
from eve_dolphin.sync.planetary_models import (
    ExtractorDetails,
    PlanetColony,
    PlanetPin,
    PlanetPinContent,
)
from eve_dolphin.sync.planetary_repository import PlanetarySnapshotRepository

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def test_catalog_derives_p0_to_p4_tiers_and_universe_names(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)

    catalog = PiCatalogRepository(database).load("de")
    locations = PiCatalogRepository(database).locations((4001,), "de")

    assert catalog.commodities[1].tier is PiTier.RAW
    assert catalog.commodities[11].tier is PiTier.BASIC
    assert catalog.commodities[21].tier is PiTier.REFINED
    assert catalog.commodities[31].tier is PiTier.SPECIALIZED
    assert catalog.commodities[41].tier is PiTier.ADVANCED
    assert catalog.recipes_by_output[21].output.quantity == 5
    assert [
        (item.commodity.type_id, item.quantity) for item in catalog.recipes_by_output[21].inputs
    ] == [
        (11, 40),
        (12, 40),
    ]
    assert locations[4001].planet_name == "Testsystem IV"
    assert locations[4001].solar_system_name == "Testsystem"
    assert locations[4001].security_status == Decimal("-0.25")


def test_planner_resolves_exact_p2_p3_and_p4_quantities(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profiles = PiProfileRepository(database)
    profile = profiles.list_all()[0]
    assert profile.profile_id is not None
    planner = PiPlannerService(database, clock=lambda: NOW)

    p2 = planner.plan(PiPlanRequest(21, 10, 2, profile.profile_id), "en")
    p3 = planner.plan(PiPlanRequest(31, 3, 2, profile.profile_id), "en")
    p4 = planner.plan(PiPlanRequest(41, 1, 2, profile.profile_id), "en")

    assert _line(p2, 21).cycles == 2
    assert _line(p2, 21).gross_cycles == 2
    assert _line(p2, 11).required == 80
    assert _line(p2, 12).required == 80
    assert _line(p2, 1).import_quantity == 12_000
    assert _line(p2, 2).import_quantity == 12_000

    assert _line(p3, 31).cycles == 1
    assert _line(p3, 21).required == 10
    assert _line(p3, 22).required == 10
    assert _line(p3, 1).import_quantity == 24_000
    assert _line(p3, 2).import_quantity == 24_000

    assert _line(p4, 41).cycles == 1
    assert _line(p4, 31).required == 6
    assert _line(p4, 32).required == 6
    assert _line(p4, 1).import_quantity == 96_000
    assert _line(p4, 2).import_quantity == 96_000
    assert p4.import_tax_isk == Decimal("48000")
    assert p4.export_tax_isk == Decimal("120000")
    assert p4.total_logistics_isk == Decimal("168000.000")
    assert "factory_capacity_shortfall" in p4.blocked_reasons
    assert _line(p4, 41).additional_factories == 1
    assert not p4.is_feasible


def test_existing_factory_capacity_makes_target_executable(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    _activate_factories(database, (101, 102, 201))
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(21, 10, 2, profile.profile_id), "en"
    )

    assert _line(result, 21).cycles == 2
    assert _line(result, 21).available_factory_cycles == 48
    assert _line(result, 21).additional_factories == 0
    assert _line(result, 11).available_factory_cycles == 96
    assert result.is_feasible


def test_wormhole_without_poco_blocks_required_imports(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = next(
        value
        for value in PiProfileRepository(database).list_all()
        if value.name == "Wurmloch ohne POCO"
    )
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(21, 10, 1, profile.profile_id), "de"
    )

    assert "imports_require_customs_office" in result.blocked_reasons
    assert result.import_volume_m3 > 0
    assert not result.is_feasible


def test_planner_distinguishes_extraction_from_purchased_inputs(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None
    planner = PiPlannerService(database, clock=lambda: NOW)

    extraction = planner.plan(
        PiPlanRequest(
            21,
            10,
            2,
            profile.profile_id,
            PiOperationMode.EXTRACTOR,
            PiTier.RAW,
            PiStorageStrategy.BUFFERED,
        ),
        "en",
    )
    purchased = planner.plan(
        PiPlanRequest(
            21,
            10,
            2,
            profile.profile_id,
            PiOperationMode.IMPORT,
            PiTier.BASIC,
            PiStorageStrategy.DIRECT,
        ),
        "en",
    )

    assert _line(extraction, 1).source_quantity == 12_000
    assert _line(extraction, 1).import_quantity == 0
    assert _line(purchased, 11).import_quantity == 80
    assert all(line.commodity.tier is not PiTier.RAW for line in purchased.lines)
    assert any(stage.buffer_storage for stage in extraction.layout)
    assert not any(stage.buffer_storage for stage in purchased.layout)


def test_launchpad_goal_derives_quantity_and_exact_fill_time(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            21,
            1,
            1,
            profile.profile_id,
            source_tier=PiTier.BASIC,
            goal_mode=PiGoalMode.LAUNCHPAD,
            launchpad_capacity_m3=Decimal("10"),
            input_launchpads=4,
            final_factories=2,
        ),
        "en",
    )

    assert result.request.target_quantity == 5
    assert result.launchpad_fill is not None
    assert result.launchpad_fill.product_quantity == 5
    assert result.launchpad_fill.product_volume_m3 == Decimal("7.5")
    assert result.launchpad_fill.unused_volume_m3 == Decimal("2.5")
    assert result.launchpad_fill.fill_time == timedelta(hours=1)
    assert result.launchpad_fill.final_factories == 2
    assert next(stage for stage in result.layout if stage.commodity.type_id == 21).factories == 2
    assert all(
        stage.factories == 1 for stage in result.layout if stage.commodity.type_id in {11, 12}
    )
    assert all(line.excess_quantity == 0 for line in result.lines)


def test_launchpad_reverse_plan_ignores_other_colony_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None
    planner = PiPlannerService(database, clock=lambda: NOW)

    monkeypatch.setattr(
        planner,
        "_planning_state",
        lambda _catalog, _now, _window: (
            Counter({21: 1_000, 11: 1_000, 12: 1_000}),
            Counter({21: 1_000, 11: 1_000, 12: 1_000}),
        ),
    )
    result = planner.plan(
        PiPlanRequest(
            21,
            1,
            1,
            profile.profile_id,
            source_tier=PiTier.BASIC,
            goal_mode=PiGoalMode.LAUNCHPAD,
            launchpad_capacity_m3=Decimal("10"),
            input_launchpads=4,
        ),
        "en",
    )

    assert result.request.target_quantity == 5
    assert _line(result, 21).cycles == 1
    assert _line(result, 11).import_quantity == 40
    assert _line(result, 12).import_quantity == 40
    assert all(line.available_at_deadline == 0 for line in result.lines)
    assert all(line.used_from_available == 0 for line in result.lines)
    assert all(line.factory_shortfall_cycles == 0 for line in result.lines)
    assert "factory_capacity_shortfall" not in result.blocked_reasons


def test_launchpad_reverse_plan_steps_down_to_zero_intermediate_excess(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    _add_non_divisible_reverse_chain(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            23,
            1,
            1,
            profile.profile_id,
            source_tier=PiTier.RAW,
            goal_mode=PiGoalMode.LAUNCHPAD,
            launchpad_capacity_m3=Decimal("100"),
        ),
        "en",
    )

    assert result.request.target_quantity == 64
    assert _line(result, 23).required == 64
    assert _line(result, 13).required == 192
    assert _line(result, 13).planned_output == 192
    assert _line(result, 3).import_quantity == 144
    assert all(line.excess_quantity == 0 for line in result.lines)


def test_launchpad_goal_never_overfills_with_partial_output_batch(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            21,
            1,
            1,
            profile.profile_id,
            source_tier=PiTier.BASIC,
            goal_mode=PiGoalMode.LAUNCHPAD,
            launchpad_capacity_m3=Decimal("10000"),
        ),
        "en",
    )

    assert result.request.target_quantity == 1_640
    assert _line(result, 21).gross_cycles == 328
    assert result.launchpad_fill is not None
    assert result.launchpad_fill.product_volume_m3 == Decimal("2460.0")
    assert result.launchpad_fill.unused_volume_m3 == Decimal("7540.0")
    assert result.launchpad_fill.input_launchpads == 1
    assert result.launchpad_fill.input_volume_m3 == Decimal("9971.20")
    assert result.launchpad_fill.input_capacity_m3 == Decimal("10000")


def test_plan_reports_command_center_cpu_and_power_budget(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            21,
            10,
            2,
            profile.profile_id,
            operation_mode=PiOperationMode.IMPORT,
            source_tier=PiTier.BASIC,
            command_center_level=5,
            infrastructure_reserve_percent=Decimal("10"),
        ),
        "en",
    )

    budget = result.infrastructure_budget
    assert budget is not None
    assert (budget.total_cpu, budget.total_power) == (25_415, 19_000)
    assert (budget.reserved_cpu, budget.reserved_power) == (2_542, 1_900)
    assert (budget.used_cpu, budget.used_power) == (4_100, 1_400)
    assert budget.maximum_layout_copies == 23
    assert budget.maximum_final_factories == 23
    assert budget.required_planet_types == ()


def test_p4_layout_requires_barren_or_temperate_planet(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            41,
            1,
            2,
            profile.profile_id,
            operation_mode=PiOperationMode.IMPORT,
            source_tier=PiTier.SPECIALIZED,
        ),
        "en",
    )

    budget = result.infrastructure_budget
    assert budget is not None
    assert budget.high_tech_factories == 1
    assert budget.required_planet_types == ("barren", "temperate")


def test_p4_launchpad_goal_uses_selected_purchase_tier_for_initial_load(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            41,
            1,
            1,
            profile.profile_id,
            operation_mode=PiOperationMode.IMPORT,
            source_tier=PiTier.REFINED,
            goal_mode=PiGoalMode.LAUNCHPAD,
            launchpad_capacity_m3=Decimal("10000"),
            input_launchpads=1,
        ),
        "en",
    )

    fill = result.launchpad_fill
    assert fill is not None
    assert result.request.target_quantity == 83
    assert fill.input_volume_m3 == Decimal("9960.0")
    assert tuple((item.type_id, quantity) for item, quantity in fill.input_quantities) == (
        (21, 3320),
        (22, 3320),
    )


@pytest.mark.parametrize(
    ("target_type_id", "source_tier", "input_launchpads"),
    [
        (target_type_id, PiTier(source_tier), input_launchpads)
        for target_type_id, target_tier in ((11, 1), (21, 2), (31, 3), (41, 4))
        for source_tier in range(target_tier)
        for input_launchpads in (1, 2, 3, 4, 5)
    ],
)
def test_every_launchpad_target_and_source_tier_combination_is_volume_exact(
    tmp_path: Path,
    target_type_id: int,
    source_tier: PiTier,
    input_launchpads: int,
) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None
    planner = PiPlannerService(database, clock=lambda: NOW)
    request = PiPlanRequest(
        target_type_id,
        1,
        1,
        profile.profile_id,
        operation_mode=PiOperationMode.IMPORT,
        source_tier=source_tier,
        goal_mode=PiGoalMode.LAUNCHPAD,
        launchpad_capacity_m3=Decimal("10000"),
        input_launchpads=input_launchpads,
    )

    result = planner.plan(request, "en")
    fill = result.launchpad_fill
    assert fill is not None
    recipe = PiCatalogRepository(database).load("en").recipes_by_output[target_type_id]
    cycles = result.request.target_quantity // recipe.output.quantity
    assert result.request.target_quantity == cycles * recipe.output.quantity
    assert fill.product_volume_m3 <= fill.capacity_m3
    assert fill.input_volume_m3 <= fill.input_capacity_m3
    assert all(item.tier <= source_tier for item, _quantity in fill.input_quantities)
    assert all(line.excess_quantity == 0 for line in result.lines)

    cargo_quantities: Counter[int] = Counter()
    cargo_volumes: dict[int, Decimal] = {}
    branch_cargo: dict[tuple[int, int], Counter[int]] = {}
    branch_totals: dict[int, Counter[int]] = {}
    for cargo in fill.input_cargo:
        cargo_quantities[cargo.commodity.type_id] += cargo.quantity
        cargo_volumes[cargo.launchpad_index] = (
            cargo_volumes.get(cargo.launchpad_index, Decimal(0)) + cargo.volume_m3
        )
        branch_cargo.setdefault((cargo.launchpad_index, cargo.branch_commodity.type_id), Counter())[
            cargo.commodity.type_id
        ] += cargo.quantity
        branch_totals.setdefault(cargo.branch_commodity.type_id, Counter())[
            cargo.commodity.type_id
        ] += cargo.quantity
    assert cargo_quantities == Counter(
        {item.type_id: quantity for item, quantity in fill.input_quantities}
    )
    assert all(volume <= fill.capacity_m3 for volume in cargo_volumes.values())
    assert all(1 <= launchpad_index <= input_launchpads for launchpad_index in cargo_volumes)
    for (_launchpad_index, branch_type_id), quantities in branch_cargo.items():
        totals = branch_totals[branch_type_id]
        first_type_id = next(iter(totals))
        assert set(quantities) == set(totals)
        for type_id in totals:
            assert (
                quantities[type_id] * totals[first_type_id]
                == quantities[first_type_id] * totals[type_id]
            )

    next_quantity = (cycles + 1) * recipe.output.quantity
    next_result = planner.plan(
        PiPlanRequest(
            target_type_id,
            next_quantity,
            365,
            profile.profile_id,
            operation_mode=PiOperationMode.IMPORT,
            source_tier=source_tier,
        ),
        "en",
    )
    next_input_volume = sum(
        Decimal(line.import_quantity) * line.commodity.volume_m3 for line in next_result.lines
    )
    next_output_volume = Decimal(next_quantity) * result.target.volume_m3
    assert next_input_volume > fill.input_capacity_m3 or next_output_volume > fill.capacity_m3


def test_one_input_launchpad_can_hold_multiple_starting_products(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            21,
            1,
            1,
            profile.profile_id,
            source_tier=PiTier.BASIC,
            goal_mode=PiGoalMode.LAUNCHPAD,
            input_launchpads=1,
        ),
        "en",
    )

    fill = result.launchpad_fill
    assert fill is not None
    first_launchpad_products = {
        cargo.commodity.type_id for cargo in fill.input_cargo if cargo.launchpad_index == 1
    }
    assert first_launchpad_products == {11, 12}


def test_starting_products_are_grouped_by_final_recipe_branch(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            41,
            1,
            1,
            profile.profile_id,
            source_tier=PiTier.REFINED,
            goal_mode=PiGoalMode.LAUNCHPAD,
            input_launchpads=2,
        ),
        "en",
    )

    fill = result.launchpad_fill
    assert fill is not None
    cargo_by_branch: dict[tuple[int, int], Counter[int]] = {}
    for cargo in fill.input_cargo:
        cargo_by_branch.setdefault(
            (cargo.launchpad_index, cargo.branch_commodity.type_id), Counter()
        )[cargo.commodity.type_id] += cargo.quantity
    assert cargo_by_branch == {
        (1, 31): Counter({21: 2000, 22: 2000}),
        (2, 32): Counter({21: 2000, 22: 2000}),
    }


def test_low_command_center_level_blocks_oversized_layout(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            21,
            10,
            2,
            profile.profile_id,
            operation_mode=PiOperationMode.IMPORT,
            source_tier=PiTier.BASIC,
            command_center_level=0,
        ),
        "en",
    )

    assert result.infrastructure_budget is not None
    assert result.infrastructure_budget.remaining_cpu < 0
    assert "planet_cpu_shortfall" in result.blocked_reasons


def test_extractor_plan_counts_ecus_heads_and_buffer_storage(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    result = PiPlannerService(database, clock=lambda: NOW).plan(
        PiPlanRequest(
            21,
            10,
            2,
            profile.profile_id,
            operation_mode=PiOperationMode.EXTRACTOR,
            storage_strategy=PiStorageStrategy.BUFFERED,
            extractor_heads_per_ecu=5,
        ),
        "en",
    )

    budget = result.infrastructure_budget
    assert budget is not None
    assert budget.extractor_control_units == 2
    assert budget.extractor_heads == 10
    assert budget.storage_facilities == 1
    assert budget.basic_factories == 2
    assert budget.advanced_factories == 1
    assert (budget.used_cpu, budget.used_power) == (6_900, 14_400)
    assert budget.maximum_layout_copies == 1


def test_launchpad_goal_rejects_product_larger_than_capacity(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None

    with pytest.raises(ValueError, match="does not fit"):
        PiPlannerService(database, clock=lambda: NOW).plan(
            PiPlanRequest(
                41,
                1,
                1,
                profile.profile_id,
                goal_mode=PiGoalMode.LAUNCHPAD,
                launchpad_capacity_m3=Decimal("10"),
            ),
            "en",
        )


def test_saved_pi_plans_can_be_created_edited_and_deleted(tmp_path: Path) -> None:
    database = _database(tmp_path)
    profile = PiProfileRepository(database).list_all()[0]
    assert profile.profile_id is not None
    repository = SavedPiPlanRepository(database)
    request = PiPlanRequest(
        21,
        500,
        7,
        profile.profile_id,
        PiOperationMode.IMPORT,
        PiTier.BASIC,
        PiStorageStrategy.BUFFERED,
        PiGoalMode.LAUNCHPAD,
        Decimal("10000"),
        2,
        3,
        4,
        Decimal("12.5"),
        7,
    )

    stored = repository.save(SavedPiPlan(None, "P2 Fabrikplanet", request))
    assert stored.plan_id is not None
    assert repository.list_all() == (stored,)
    assert stored.request.goal_mode is PiGoalMode.LAUNCHPAD
    assert stored.request.launchpad_capacity_m3 == Decimal("10000")
    assert stored.request.input_launchpads == 2
    assert stored.request.final_factories == 3
    assert stored.request.command_center_level == 4
    assert stored.request.infrastructure_reserve_percent == Decimal("12.5")
    assert stored.request.extractor_heads_per_ecu == 7

    edited = repository.save(SavedPiPlan(stored.plan_id, "P2 Woche", request))
    assert edited.name == "P2 Woche"
    repository.delete(stored.plan_id)
    assert repository.list_all() == ()


def test_factory_colony_shows_storage_and_ten_hour_supply_countdown(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _seed_catalog(database)
    character = EveCharacter(1001, "Factory Pilot", None, (), NOW)
    CharacterRepository(database).upsert(character)
    pins = (
        PlanetPin(
            1,
            9001,
            Decimal(0),
            Decimal(0),
            (PlanetPinContent(11, 80), PlanetPinContent(12, 80)),
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        PlanetPin(
            2,
            9999,
            Decimal(0),
            Decimal(0),
            (),
            None,
            None,
            None,
            None,
            None,
            201,
        ),
    )
    colony = PlanetColony(4001, 1001, 3001, "temperate", NOW, 5, 2, None, pins, (), ())
    snapshots = PlanetarySnapshotRepository(database)
    run_id = snapshots.start_run(character.character_id, NOW)
    snapshots.activate(run_id, character.character_id, NOW, (colony,), None)

    result = PlanetaryOverviewService(database, clock=lambda: NOW).list_colonies("en")[0]

    assert result.operation_mode is PiOperationMode.IMPORT
    assert result.supply_exhausted_at == NOW + timedelta(hours=2)
    assert result.attention_remaining == timedelta(hours=2)
    assert "supply_ending_soon" in result.warning_codes
    assert len(result.storage_nodes) == 1
    assert result.storage_nodes[0].used_m3 == Decimal("60.80")
    assert result.storage_nodes[0].capacity_m3 == Decimal("12000")


def test_profiles_are_persistent_and_decimal_exact(tmp_path: Path) -> None:
    database = _database(tmp_path)
    repository = PiProfileRepository(database)

    defaults = repository.list_all()
    stored = repository.save(
        PiProfile(
            None,
            "J151141",
            SpaceKind.WORMHOLE,
            True,
            Decimal("2.5"),
            Decimal("5.75"),
            Decimal("125.50"),
            Decimal("62000"),
            Decimal("15"),
            PiTier.REFINED,
        )
    )

    assert len(defaults) == 3
    assert stored.profile_id is not None
    assert repository.get(stored.profile_id) == stored


def test_forecast_uses_extractor_and_factory_cycles_and_storage_capacity() -> None:
    raw = PiCommodity(1, "Raw", Decimal("0.01"), PiTier.RAW)
    basic = PiCommodity(11, "Basic", Decimal("0.38"), PiTier.BASIC)
    recipe = PiRecipe(
        101,
        "Basic",
        1800,
        (PiRecipeItem(raw, 3000),),
        PiRecipeItem(basic, 20),
    )
    catalog = PiCatalog(
        {1: raw, 11: basic},
        {11: recipe},
        {101: recipe},
        {9001: Decimal("12000")},
    )
    extractor = ExtractorDetails((), 900, Decimal("0.1"), 1, 100)
    colony = _forecast_colony(extractor, raw_amount=6_000)

    result = forecast_colony(colony, catalog, NOW, timedelta(hours=1))

    assert result.extractor_rates[0].units_per_hour == Decimal("400")
    assert result.extracted[0].quantity == 400
    assert result.factory_outputs[0].quantity == 40
    assert result.stalled_factories == 0
    assert result.constrained_factories == 0
    assert result.storage_capacity_m3 == Decimal("12000")
    assert result.storage_used_m3 == Decimal("60.00")


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "client.sqlite3", tmp_path / "backups")
    database.initialize()
    return database


def _line(result: PiPlanResult, type_id: int) -> PiPlanLine:
    return next(line for line in result.lines if line.commodity.type_id == type_id)


def _seed_catalog(database: Database) -> None:
    with database.connect() as connection, connection:
        connection.execute(
            """
            INSERT INTO sde_builds(
                build_number, release_date, source_url, archive_sha256, archive_size,
                downloaded_at, import_started_at, imported_at, activated_at, status
            ) VALUES (1, ?, 'https://example.invalid/sde.zip', ?, 1, ?, ?, ?, ?, 'ready')
            """,
            (NOW.isoformat(), "a" * 64, *(NOW.isoformat() for _ in range(4))),
        )
        connection.execute("INSERT INTO sde_current VALUES (1, 1)")
        connection.execute("INSERT INTO sde_categories VALUES (1, 1, 'PI', 'PI', 1)")
        connection.execute("INSERT INTO sde_groups VALUES (1, 1, 1, 'PI', 'PI', 1)")
        types = (
            (1, "Rohstoff A", "Raw A", "0.01", None),
            (2, "Rohstoff B", "Raw B", "0.01", None),
            (11, "P1 A", "P1 A", "0.38", None),
            (12, "P1 B", "P1 B", "0.38", None),
            (21, "P2 A", "P2 A", "1.5", None),
            (22, "P2 B", "P2 B", "1.5", None),
            (31, "P3 A", "P3 A", "6", None),
            (32, "P3 B", "P3 B", "6", None),
            (41, "P4", "P4", "100", None),
            (9001, "Lager", "Storage", "1", "12000"),
        )
        connection.executemany(
            """
            INSERT INTO sde_types(
                build_number, type_id, group_id, market_group_id, name_de, name_en,
                volume, mass, portion_size, published, capacity
            ) VALUES (1, ?, 1, NULL, ?, ?, ?, NULL, 1, 1, ?)
            """,
            types,
        )
        recipes = (
            (101, 1800, "P1 A", 11, 20, ((1, 3000),)),
            (102, 1800, "P1 B", 12, 20, ((2, 3000),)),
            (201, 3600, "P2 A", 21, 5, ((11, 40), (12, 40))),
            (202, 3600, "P2 B", 22, 5, ((11, 40), (12, 40))),
            (301, 3600, "P3 A", 31, 3, ((21, 10), (22, 10))),
            (302, 3600, "P3 B", 32, 3, ((21, 10), (22, 10))),
            (401, 3600, "P4", 41, 1, ((31, 6), (32, 6))),
        )
        for schematic_id, seconds, name, output_id, output_qty, inputs in recipes:
            connection.execute(
                "INSERT INTO sde_planet_schematics VALUES (1, ?, ?, ?, ?)",
                (schematic_id, seconds, name, name),
            )
            connection.executemany(
                "INSERT INTO sde_planet_schematic_types VALUES (1, ?, ?, 1, ?)",
                ((schematic_id, type_id, quantity) for type_id, quantity in inputs),
            )
            connection.execute(
                "INSERT INTO sde_planet_schematic_types VALUES (1, ?, ?, 0, ?)",
                (schematic_id, output_id, output_qty),
            )
        connection.execute(
            """
            INSERT INTO sde_solar_systems
            VALUES (1, 3001, 2001, 1001, 'Testsystem', 'Test System', -0.25)
            """
        )
        connection.execute("INSERT INTO sde_planets VALUES (1, 4001, 3001, 4, 9001)")


def _add_non_divisible_reverse_chain(database: Database) -> None:
    with database.connect() as connection, connection:
        connection.executemany(
            """
            INSERT INTO sde_types(
                build_number, type_id, group_id, market_group_id, name_de, name_en,
                volume, mass, portion_size, published, capacity
            ) VALUES (1, ?, 1, NULL, ?, ?, ?, NULL, 1, 1, NULL)
            """,
            (
                (3, "Rohstoff C", "Raw C", "0.01"),
                (13, "P1 C", "P1 C", "0.38"),
                (23, "P2 C", "P2 C", "1.5"),
            ),
        )
        connection.executemany(
            "INSERT INTO sde_planet_schematics VALUES (1, ?, 3600, ?, ?)",
            ((103, "P1 C", "P1 C"), (203, "P2 C", "P2 C")),
        )
        connection.executemany(
            "INSERT INTO sde_planet_schematic_types VALUES (1, ?, ?, ?, ?)",
            (
                (103, 3, 1, 3),
                (103, 13, 0, 4),
                (203, 13, 1, 3),
                (203, 23, 0, 1),
            ),
        )


def _forecast_colony(extractor: ExtractorDetails, raw_amount: int) -> PlanetColony:
    extractor_pin = PlanetPin(
        1,
        9998,
        Decimal("0"),
        Decimal("0"),
        (),
        None,
        NOW + timedelta(hours=2),
        NOW - timedelta(hours=1),
        NOW,
        extractor,
        None,
    )
    storage_pin = PlanetPin(
        2,
        9001,
        Decimal("0"),
        Decimal("0"),
        (PlanetPinContent(1, raw_amount),),
        None,
        None,
        None,
        None,
        None,
        None,
    )
    factory_pin = PlanetPin(
        3,
        9999,
        Decimal("0"),
        Decimal("0"),
        (),
        None,
        None,
        None,
        None,
        None,
        101,
    )
    return PlanetColony(
        4001,
        1001,
        3001,
        "temperate",
        NOW,
        5,
        3,
        None,
        (extractor_pin, storage_pin, factory_pin),
        (),
        (),
    )


def _activate_factories(database: Database, schematic_ids: tuple[int, ...]) -> None:
    character = EveCharacter(1001, "PI Pilot", None, (), NOW)
    CharacterRepository(database).upsert(character)
    pins = tuple(
        PlanetPin(
            pin_id=index,
            type_id=9999,
            latitude=Decimal("0"),
            longitude=Decimal("0"),
            contents=(),
            schematic_id=None,
            expiry_time=None,
            install_time=None,
            last_cycle_start=None,
            extractor_details=None,
            factory_schematic_id=schematic_id,
        )
        for index, schematic_id in enumerate(schematic_ids, start=1)
    )
    colony = PlanetColony(
        planet_id=4001,
        owner_id=character.character_id,
        solar_system_id=3001,
        planet_type="temperate",
        last_update=NOW,
        upgrade_level=5,
        num_pins=len(pins),
        layout_last_modified=None,
        pins=pins,
        links=(),
        routes=(),
    )
    repository = PlanetarySnapshotRepository(database)
    run_id = repository.start_run(character.character_id, NOW)
    repository.activate(run_id, character.character_id, NOW, (colony,), None)

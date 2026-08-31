"""Ordered, transactional SQLite schema migrations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    description: str
    sql: str


MIGRATIONS = (
    Migration(
        version=1,
        description="local profile, characters and synchronization foundation",
        sql="""
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE eve_characters (
            character_id INTEGER PRIMARY KEY,
            character_name TEXT NOT NULL,
            owner_hash TEXT,
            granted_scopes_json TEXT NOT NULL DEFAULT '[]',
            linked_at TEXT NOT NULL,
            last_sync_at TEXT
        );

        CREATE TABLE sync_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER,
            sync_kind TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'cancelled')),
            started_at TEXT NOT NULL,
            finished_at TEXT,
            message TEXT,
            FOREIGN KEY (character_id) REFERENCES eve_characters(character_id) ON DELETE CASCADE
        );

        CREATE INDEX sync_runs_character_started_idx
            ON sync_runs(character_id, started_at DESC);
        """,
    ),
    Migration(
        version=2,
        description="character authorization health",
        sql="""
        ALTER TABLE eve_characters
            ADD COLUMN authorization_status TEXT NOT NULL DEFAULT 'active'
            CHECK (authorization_status IN ('active', 'reauthorization_required'));

        ALTER TABLE eve_characters
            ADD COLUMN authorization_error_at TEXT;
        """,
    ),
    Migration(
        version=3,
        description="versioned production SDE foundation",
        sql="""
        CREATE TABLE sde_builds (
            build_number INTEGER PRIMARY KEY CHECK (build_number > 0),
            release_date TEXT NOT NULL,
            source_url TEXT NOT NULL,
            archive_sha256 TEXT NOT NULL CHECK (length(archive_sha256) = 64),
            archive_size INTEGER NOT NULL CHECK (archive_size > 0),
            metadata_etag TEXT,
            metadata_last_modified TEXT,
            archive_etag TEXT,
            archive_last_modified TEXT,
            downloaded_at TEXT NOT NULL,
            import_started_at TEXT NOT NULL,
            imported_at TEXT,
            activated_at TEXT,
            status TEXT NOT NULL CHECK (status IN ('importing', 'ready', 'failed')),
            failure_reason TEXT
        );

        CREATE TABLE sde_current (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            build_number INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number)
        );

        CREATE TABLE sde_dataset_counts (
            build_number INTEGER NOT NULL,
            dataset TEXT NOT NULL,
            record_count INTEGER NOT NULL CHECK (record_count >= 0),
            PRIMARY KEY (build_number, dataset),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE
        );

        CREATE TABLE sde_import_warnings (
            build_number INTEGER NOT NULL,
            warning TEXT NOT NULL,
            record_count INTEGER NOT NULL CHECK (record_count > 0),
            PRIMARY KEY (build_number, warning),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE
        );

        CREATE TABLE sde_categories (
            build_number INTEGER NOT NULL,
            category_id INTEGER NOT NULL CHECK (category_id >= 0),
            name_de TEXT NOT NULL,
            name_en TEXT NOT NULL,
            published INTEGER NOT NULL CHECK (published IN (0, 1)),
            PRIMARY KEY (build_number, category_id),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE
        );

        CREATE TABLE sde_market_groups (
            build_number INTEGER NOT NULL,
            market_group_id INTEGER NOT NULL CHECK (market_group_id >= 0),
            parent_group_id INTEGER,
            name_de TEXT NOT NULL,
            name_en TEXT NOT NULL,
            has_types INTEGER NOT NULL CHECK (has_types IN (0, 1)),
            PRIMARY KEY (build_number, market_group_id),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE
        );

        CREATE TABLE sde_groups (
            build_number INTEGER NOT NULL,
            group_id INTEGER NOT NULL CHECK (group_id >= 0),
            category_id INTEGER NOT NULL,
            name_de TEXT NOT NULL,
            name_en TEXT NOT NULL,
            published INTEGER NOT NULL CHECK (published IN (0, 1)),
            PRIMARY KEY (build_number, group_id),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE,
            FOREIGN KEY (build_number, category_id)
                REFERENCES sde_categories(build_number, category_id)
        );

        CREATE TABLE sde_types (
            build_number INTEGER NOT NULL,
            type_id INTEGER NOT NULL CHECK (type_id >= 0),
            group_id INTEGER NOT NULL,
            market_group_id INTEGER,
            name_de TEXT NOT NULL,
            name_en TEXT NOT NULL,
            volume REAL,
            mass REAL,
            portion_size INTEGER,
            published INTEGER NOT NULL CHECK (published IN (0, 1)),
            PRIMARY KEY (build_number, type_id),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE,
            FOREIGN KEY (build_number, group_id)
                REFERENCES sde_groups(build_number, group_id),
            FOREIGN KEY (build_number, market_group_id)
                REFERENCES sde_market_groups(build_number, market_group_id)
        );

        CREATE TABLE sde_blueprints (
            build_number INTEGER NOT NULL,
            blueprint_type_id INTEGER NOT NULL,
            max_production_limit INTEGER,
            PRIMARY KEY (build_number, blueprint_type_id),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE,
            FOREIGN KEY (build_number, blueprint_type_id)
                REFERENCES sde_types(build_number, type_id)
        );

        CREATE TABLE sde_blueprint_activities (
            build_number INTEGER NOT NULL,
            blueprint_type_id INTEGER NOT NULL,
            activity TEXT NOT NULL,
            time_seconds INTEGER,
            PRIMARY KEY (build_number, blueprint_type_id, activity),
            FOREIGN KEY (build_number, blueprint_type_id)
                REFERENCES sde_blueprints(build_number, blueprint_type_id) ON DELETE CASCADE
        );

        CREATE TABLE sde_blueprint_materials (
            build_number INTEGER NOT NULL,
            blueprint_type_id INTEGER NOT NULL,
            activity TEXT NOT NULL,
            material_type_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            PRIMARY KEY (build_number, blueprint_type_id, activity, material_type_id),
            FOREIGN KEY (build_number, blueprint_type_id, activity)
                REFERENCES sde_blueprint_activities(build_number, blueprint_type_id, activity)
                ON DELETE CASCADE
        );

        CREATE TABLE sde_blueprint_products (
            build_number INTEGER NOT NULL,
            blueprint_type_id INTEGER NOT NULL,
            activity TEXT NOT NULL,
            product_type_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            probability REAL,
            PRIMARY KEY (build_number, blueprint_type_id, activity, product_type_id),
            FOREIGN KEY (build_number, blueprint_type_id, activity)
                REFERENCES sde_blueprint_activities(build_number, blueprint_type_id, activity)
                ON DELETE CASCADE
        );

        CREATE TABLE sde_planet_schematics (
            build_number INTEGER NOT NULL,
            schematic_id INTEGER NOT NULL CHECK (schematic_id >= 0),
            cycle_time_seconds INTEGER NOT NULL CHECK (cycle_time_seconds > 0),
            name_de TEXT NOT NULL,
            name_en TEXT NOT NULL,
            PRIMARY KEY (build_number, schematic_id),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE
        );

        CREATE TABLE sde_planet_schematic_types (
            build_number INTEGER NOT NULL,
            schematic_id INTEGER NOT NULL,
            type_id INTEGER NOT NULL,
            is_input INTEGER NOT NULL CHECK (is_input IN (0, 1)),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            PRIMARY KEY (build_number, schematic_id, type_id),
            FOREIGN KEY (build_number, schematic_id)
                REFERENCES sde_planet_schematics(build_number, schematic_id) ON DELETE CASCADE,
            FOREIGN KEY (build_number, type_id)
                REFERENCES sde_types(build_number, type_id)
        );

        CREATE INDEX sde_types_name_en_idx ON sde_types(build_number, name_en);
        CREATE INDEX sde_types_name_de_idx ON sde_types(build_number, name_de);
        CREATE INDEX sde_blueprint_products_type_idx
            ON sde_blueprint_products(build_number, product_type_id);
        CREATE INDEX sde_blueprint_materials_type_idx
            ON sde_blueprint_materials(build_number, material_type_id);
        """,
    ),
    Migration(
        version=4,
        description="atomic character asset and blueprint snapshots",
        sql="""
        CREATE TABLE industry_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            fetched_at TEXT NOT NULL,
            assets_last_modified TEXT,
            blueprints_last_modified TEXT,
            asset_count INTEGER NOT NULL CHECK (asset_count >= 0),
            blueprint_count INTEGER NOT NULL CHECK (blueprint_count >= 0),
            UNIQUE (id, character_id),
            FOREIGN KEY (character_id) REFERENCES eve_characters(character_id) ON DELETE CASCADE
        );

        CREATE TABLE industry_current (
            character_id INTEGER PRIMARY KEY,
            snapshot_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (character_id) REFERENCES eve_characters(character_id) ON DELETE CASCADE,
            FOREIGN KEY (snapshot_id, character_id)
                REFERENCES industry_snapshots(id, character_id)
        );

        CREATE TABLE character_assets (
            snapshot_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            type_id INTEGER NOT NULL CHECK (type_id > 0),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            location_id INTEGER NOT NULL,
            location_type TEXT NOT NULL
                CHECK (location_type IN ('station', 'solar_system', 'item', 'other')),
            location_flag TEXT NOT NULL,
            is_singleton INTEGER NOT NULL CHECK (is_singleton IN (0, 1)),
            is_blueprint_copy INTEGER CHECK (is_blueprint_copy IN (0, 1)),
            PRIMARY KEY (snapshot_id, item_id),
            FOREIGN KEY (snapshot_id) REFERENCES industry_snapshots(id) ON DELETE CASCADE
        );

        CREATE TABLE character_blueprints (
            snapshot_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            type_id INTEGER NOT NULL CHECK (type_id > 0),
            location_id INTEGER NOT NULL,
            location_flag TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity >= -2 AND quantity != 0),
            time_efficiency INTEGER NOT NULL,
            material_efficiency INTEGER NOT NULL,
            runs INTEGER NOT NULL CHECK (runs >= -1),
            PRIMARY KEY (snapshot_id, item_id),
            FOREIGN KEY (snapshot_id) REFERENCES industry_snapshots(id) ON DELETE CASCADE
        );

        CREATE INDEX character_assets_type_idx
            ON character_assets(snapshot_id, type_id);
        CREATE INDEX character_assets_location_idx
            ON character_assets(snapshot_id, location_id);
        CREATE INDEX character_blueprints_type_idx
            ON character_blueprints(snapshot_id, type_id);
        """,
    ),
    Migration(
        version=5,
        description="atomic character industry job snapshots",
        sql="""
        CREATE TABLE industry_job_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            fetched_at TEXT NOT NULL,
            last_modified TEXT,
            job_count INTEGER NOT NULL CHECK (job_count >= 0),
            UNIQUE (id, character_id),
            FOREIGN KEY (character_id) REFERENCES eve_characters(character_id) ON DELETE CASCADE
        );

        CREATE TABLE industry_jobs_current (
            character_id INTEGER PRIMARY KEY,
            snapshot_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (character_id) REFERENCES eve_characters(character_id) ON DELETE CASCADE,
            FOREIGN KEY (snapshot_id, character_id)
                REFERENCES industry_job_snapshots(id, character_id)
        );

        CREATE TABLE character_industry_jobs (
            snapshot_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            installer_id INTEGER NOT NULL,
            facility_id INTEGER NOT NULL,
            station_id INTEGER NOT NULL,
            activity_id INTEGER NOT NULL CHECK (activity_id > 0),
            blueprint_id INTEGER NOT NULL,
            blueprint_type_id INTEGER NOT NULL CHECK (blueprint_type_id > 0),
            blueprint_location_id INTEGER NOT NULL,
            output_location_id INTEGER NOT NULL,
            runs INTEGER NOT NULL CHECK (runs > 0),
            status TEXT NOT NULL
                CHECK (status IN (
                    'active', 'cancelled', 'delivered', 'paused', 'ready', 'reverted'
                )),
            duration_seconds INTEGER NOT NULL CHECK (duration_seconds >= 0),
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            completed_character_id INTEGER,
            completed_date TEXT,
            pause_date TEXT,
            cost_decimal TEXT,
            licensed_runs INTEGER,
            probability_decimal TEXT,
            product_type_id INTEGER,
            successful_runs INTEGER,
            PRIMARY KEY (snapshot_id, job_id),
            FOREIGN KEY (snapshot_id) REFERENCES industry_job_snapshots(id) ON DELETE CASCADE
        );

        CREATE INDEX character_industry_jobs_status_idx
            ON character_industry_jobs(snapshot_id, status);
        CREATE INDEX character_industry_jobs_blueprint_type_idx
            ON character_industry_jobs(snapshot_id, blueprint_type_id);
        CREATE INDEX character_industry_jobs_product_type_idx
            ON character_industry_jobs(snapshot_id, product_type_id);
        """,
    ),
    Migration(
        version=6,
        description="atomic planetary colony layout snapshots",
        sql="""
        CREATE TABLE planetary_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            fetched_at TEXT NOT NULL,
            colonies_last_modified TEXT,
            colony_count INTEGER NOT NULL CHECK (colony_count >= 0),
            pin_count INTEGER NOT NULL CHECK (pin_count >= 0),
            link_count INTEGER NOT NULL CHECK (link_count >= 0),
            route_count INTEGER NOT NULL CHECK (route_count >= 0),
            UNIQUE (id, character_id),
            FOREIGN KEY (character_id) REFERENCES eve_characters(character_id) ON DELETE CASCADE
        );

        CREATE TABLE planetary_current (
            character_id INTEGER PRIMARY KEY,
            snapshot_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (character_id) REFERENCES eve_characters(character_id) ON DELETE CASCADE,
            FOREIGN KEY (snapshot_id, character_id)
                REFERENCES planetary_snapshots(id, character_id)
        );

        CREATE TABLE character_planets (
            snapshot_id INTEGER NOT NULL,
            planet_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            solar_system_id INTEGER NOT NULL,
            planet_type TEXT NOT NULL
                CHECK (planet_type IN (
                    'temperate', 'barren', 'oceanic', 'ice', 'gas', 'lava', 'storm', 'plasma'
                )),
            last_update TEXT NOT NULL,
            upgrade_level INTEGER NOT NULL CHECK (upgrade_level >= 0),
            num_pins INTEGER NOT NULL CHECK (num_pins >= 0),
            layout_last_modified TEXT,
            PRIMARY KEY (snapshot_id, planet_id),
            FOREIGN KEY (snapshot_id) REFERENCES planetary_snapshots(id) ON DELETE CASCADE
        );

        CREATE TABLE planet_pins (
            snapshot_id INTEGER NOT NULL,
            planet_id INTEGER NOT NULL,
            pin_id INTEGER NOT NULL,
            type_id INTEGER NOT NULL CHECK (type_id > 0),
            latitude_decimal TEXT NOT NULL,
            longitude_decimal TEXT NOT NULL,
            schematic_id INTEGER,
            expiry_time TEXT,
            install_time TEXT,
            last_cycle_start TEXT,
            has_extractor_details INTEGER NOT NULL CHECK (has_extractor_details IN (0, 1)),
            extractor_cycle_time INTEGER,
            extractor_head_radius_decimal TEXT,
            extractor_product_type_id INTEGER,
            extractor_qty_per_cycle INTEGER,
            factory_schematic_id INTEGER,
            PRIMARY KEY (snapshot_id, planet_id, pin_id),
            FOREIGN KEY (snapshot_id, planet_id)
                REFERENCES character_planets(snapshot_id, planet_id) ON DELETE CASCADE
        );

        CREATE TABLE planet_pin_contents (
            snapshot_id INTEGER NOT NULL,
            planet_id INTEGER NOT NULL,
            pin_id INTEGER NOT NULL,
            type_id INTEGER NOT NULL CHECK (type_id > 0),
            amount INTEGER NOT NULL CHECK (amount >= 0),
            PRIMARY KEY (snapshot_id, planet_id, pin_id, type_id),
            FOREIGN KEY (snapshot_id, planet_id, pin_id)
                REFERENCES planet_pins(snapshot_id, planet_id, pin_id) ON DELETE CASCADE
        );

        CREATE TABLE planet_extractor_heads (
            snapshot_id INTEGER NOT NULL,
            planet_id INTEGER NOT NULL,
            pin_id INTEGER NOT NULL,
            head_id INTEGER NOT NULL CHECK (head_id >= 0),
            latitude_decimal TEXT NOT NULL,
            longitude_decimal TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, planet_id, pin_id, head_id),
            FOREIGN KEY (snapshot_id, planet_id, pin_id)
                REFERENCES planet_pins(snapshot_id, planet_id, pin_id) ON DELETE CASCADE
        );

        CREATE TABLE planet_links (
            snapshot_id INTEGER NOT NULL,
            planet_id INTEGER NOT NULL,
            source_pin_id INTEGER NOT NULL,
            destination_pin_id INTEGER NOT NULL,
            link_level INTEGER NOT NULL CHECK (link_level >= 0),
            PRIMARY KEY (snapshot_id, planet_id, source_pin_id, destination_pin_id),
            FOREIGN KEY (snapshot_id, planet_id)
                REFERENCES character_planets(snapshot_id, planet_id) ON DELETE CASCADE,
            FOREIGN KEY (snapshot_id, planet_id, source_pin_id)
                REFERENCES planet_pins(snapshot_id, planet_id, pin_id),
            FOREIGN KEY (snapshot_id, planet_id, destination_pin_id)
                REFERENCES planet_pins(snapshot_id, planet_id, pin_id)
        );

        CREATE TABLE planet_routes (
            snapshot_id INTEGER NOT NULL,
            planet_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            source_pin_id INTEGER NOT NULL,
            destination_pin_id INTEGER NOT NULL,
            content_type_id INTEGER NOT NULL CHECK (content_type_id > 0),
            quantity_decimal TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, planet_id, route_id),
            FOREIGN KEY (snapshot_id, planet_id)
                REFERENCES character_planets(snapshot_id, planet_id) ON DELETE CASCADE,
            FOREIGN KEY (snapshot_id, planet_id, source_pin_id)
                REFERENCES planet_pins(snapshot_id, planet_id, pin_id),
            FOREIGN KEY (snapshot_id, planet_id, destination_pin_id)
                REFERENCES planet_pins(snapshot_id, planet_id, pin_id)
        );

        CREATE TABLE planet_route_waypoints (
            snapshot_id INTEGER NOT NULL,
            planet_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            position INTEGER NOT NULL CHECK (position >= 0),
            pin_id INTEGER NOT NULL,
            PRIMARY KEY (snapshot_id, planet_id, route_id, position),
            FOREIGN KEY (snapshot_id, planet_id, route_id)
                REFERENCES planet_routes(snapshot_id, planet_id, route_id) ON DELETE CASCADE,
            FOREIGN KEY (snapshot_id, planet_id, pin_id)
                REFERENCES planet_pins(snapshot_id, planet_id, pin_id)
        );

        CREATE INDEX character_planets_system_idx
            ON character_planets(snapshot_id, solar_system_id);
        CREATE INDEX planet_pins_type_idx
            ON planet_pins(snapshot_id, type_id);
        CREATE INDEX planet_routes_content_idx
            ON planet_routes(snapshot_id, content_type_id);
        """,
    ),
    Migration(
        version=7,
        description="PI planning catalog and local logistics profiles",
        sql="""
        ALTER TABLE sde_types ADD COLUMN capacity REAL CHECK (capacity >= 0);

        CREATE TABLE sde_solar_systems (
            build_number INTEGER NOT NULL,
            solar_system_id INTEGER NOT NULL CHECK (solar_system_id > 0),
            constellation_id INTEGER NOT NULL CHECK (constellation_id > 0),
            region_id INTEGER NOT NULL CHECK (region_id > 0),
            name_de TEXT NOT NULL,
            name_en TEXT NOT NULL,
            security_status REAL NOT NULL,
            PRIMARY KEY (build_number, solar_system_id),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE
        );

        CREATE TABLE sde_planets (
            build_number INTEGER NOT NULL,
            planet_id INTEGER NOT NULL CHECK (planet_id > 0),
            solar_system_id INTEGER NOT NULL,
            celestial_index INTEGER NOT NULL CHECK (celestial_index > 0),
            type_id INTEGER NOT NULL,
            PRIMARY KEY (build_number, planet_id),
            FOREIGN KEY (build_number) REFERENCES sde_builds(build_number) ON DELETE CASCADE,
            FOREIGN KEY (build_number, solar_system_id)
                REFERENCES sde_solar_systems(build_number, solar_system_id) ON DELETE CASCADE,
            FOREIGN KEY (build_number, type_id)
                REFERENCES sde_types(build_number, type_id)
        );

        CREATE INDEX sde_planets_system_idx
            ON sde_planets(build_number, solar_system_id, celestial_index);

        CREATE TABLE pi_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            space_kind TEXT NOT NULL
                CHECK (space_kind IN ('highsec', 'lowsec', 'nullsec', 'wormhole')),
            has_customs_office INTEGER NOT NULL
                CHECK (has_customs_office IN (0, 1)),
            import_tax_percent_decimal TEXT NOT NULL,
            export_tax_percent_decimal TEXT NOT NULL,
            transport_isk_per_m3_decimal TEXT NOT NULL,
            cargo_capacity_m3_decimal TEXT NOT NULL,
            risk_markup_percent_decimal TEXT NOT NULL,
            supply_tier INTEGER NOT NULL CHECK (supply_tier BETWEEN 0 AND 3),
            updated_at TEXT NOT NULL
        );
        """,
    ),
    Migration(
        version=8,
        description="persistent editable PI target plans",
        sql="""
        CREATE TABLE pi_saved_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            target_type_id INTEGER NOT NULL CHECK (target_type_id > 0),
            target_quantity INTEGER NOT NULL CHECK (target_quantity > 0),
            days INTEGER NOT NULL CHECK (days BETWEEN 1 AND 365),
            profile_id INTEGER NOT NULL,
            operation_mode TEXT NOT NULL CHECK (operation_mode IN ('extractor', 'import')),
            source_tier INTEGER CHECK (source_tier BETWEEN 0 AND 3),
            storage_strategy TEXT NOT NULL CHECK (storage_strategy IN ('direct', 'buffered')),
            updated_at TEXT NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES pi_profiles(id) ON DELETE RESTRICT
        );
        """,
    ),
    Migration(
        version=9,
        description="launchpad-sized PI target plans",
        sql="""
        ALTER TABLE pi_saved_plans
            ADD COLUMN goal_mode TEXT NOT NULL DEFAULT 'manual'
            CHECK (goal_mode IN ('manual', 'launchpad'));
        ALTER TABLE pi_saved_plans
            ADD COLUMN launchpad_capacity_m3_decimal TEXT NOT NULL DEFAULT '10000';
        ALTER TABLE pi_saved_plans
            ADD COLUMN final_factories INTEGER NOT NULL DEFAULT 1
            CHECK (final_factories BETWEEN 1 AND 100);
        """,
    ),
    Migration(
        version=10,
        description="PI command-center resource budgets",
        sql="""
        ALTER TABLE pi_saved_plans
            ADD COLUMN command_center_level INTEGER NOT NULL DEFAULT 5
            CHECK (command_center_level BETWEEN 0 AND 5);
        ALTER TABLE pi_saved_plans
            ADD COLUMN infrastructure_reserve_percent_decimal TEXT NOT NULL DEFAULT '10';
        ALTER TABLE pi_saved_plans
            ADD COLUMN extractor_heads_per_ecu INTEGER NOT NULL DEFAULT 5
            CHECK (extractor_heads_per_ecu BETWEEN 1 AND 10);
        """,
    ),
)

LATEST_SCHEMA_VERSION = MIGRATIONS[-1].version

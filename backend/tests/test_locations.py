"""
NITK Campus Mobility - Location Tests.
Unit and data validation tests for Phase 1 campus data foundation.
"""

import pytest
from pydantic import ValidationError
from backend.models.location import Location, VALID_LOCATION_TYPES
from backend.services.location_service import (
    LocationService,
    get_all_locations,
    get_location_by_id,
    get_locations_by_type,
    get_locations_by_campus,
)


@pytest.fixture
def service() -> LocationService:
    """Fixture providing a freshly loaded LocationService."""
    return LocationService()


def test_location_ids_unique(service: LocationService):
    """Test that all location IDs in the dataset are strictly unique."""
    locations = service.get_all_locations()
    assert len(locations) > 0, "No locations loaded"
    ids = [loc.location_id for loc in locations]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"


def test_every_location_has_valid_type(service: LocationService):
    """Test that every location has a recognized and valid location type."""
    locations = service.get_all_locations()
    for loc in locations:
        assert loc.type in VALID_LOCATION_TYPES, (
            f"Location '{loc.location_id}' ({loc.name}) has invalid type: '{loc.type}'"
        )


def test_every_location_has_valid_campus(service: LocationService):
    """Test that every location has a valid campus classification ('EAST' or 'WEST')."""
    locations = service.get_all_locations()
    for loc in locations:
        assert loc.campus in {"EAST", "WEST"}, (
            f"Location '{loc.location_id}' has invalid campus: '{loc.campus}'"
        )


def test_required_departments_exist(service: LocationService):
    """Test that all canonical NITK academic departments exist in the dataset."""
    dept_locations = service.get_locations_by_type("department")
    dept_names = {loc.name.lower() for loc in dept_locations}
    
    expected_departments = [
        "computer science & engineering",
        "electronics & communication engineering",
        "electrical & electronics engineering",
        "information technology",
        "mechanical engineering",
        "civil engineering",
        "chemical engineering",
        "metallurgical and materials engineering",
        "mining engineering",
        "mathematical and computational sciences",
        "physics",
        "chemistry",
        "school of humanities, social sciences and management",
        "water resources and ocean engineering",
    ]

    for expected_dept in expected_departments:
        assert expected_dept in dept_names, f"Missing expected department: '{expected_dept}'"


def test_west_campus_departments(service: LocationService):
    """Test that CSE, ECE, EEE, and IT are strictly classified as WEST."""
    west_depts = {
        "dept_cse": "Computer Science & Engineering",
        "dept_ece": "Electronics & Communication Engineering",
        "dept_eee": "Electrical & Electronics Engineering",
        "dept_it": "Information Technology",
    }
    for dept_id, dept_name in west_depts.items():
        loc = service.get_location_by_id(dept_id)
        assert loc is not None, f"Department '{dept_id}' not found"
        assert loc.campus == "WEST", f"Department '{dept_name}' ({dept_id}) must be WEST, got {loc.campus}"


def test_east_campus_major_landmarks(service: LocationService):
    """Test that Main Building, Central Library, and e-Library are strictly classified as EAST."""
    main_bldg = service.get_location_by_id("loc_main_building")
    assert main_bldg is not None, "Main Building not found"
    assert main_bldg.campus == "EAST", f"Main Building must be EAST, got {main_bldg.campus}"

    central_lib = service.get_location_by_id("loc_central_library")
    assert central_lib is not None, "Central Library not found"
    assert central_lib.campus == "EAST", f"Central Library must be EAST, got {central_lib.campus}"

    e_lib = service.get_location_by_id("loc_e_library")
    assert e_lib is not None, "e-Library not found"
    assert e_lib.campus == "EAST", f"e-Library must be EAST, got {e_lib.campus}"


def test_girls_messes_are_not_present(service: LocationService):
    """Test that girls' messes are strictly excluded from the dataset per specifications."""
    locations = service.get_all_locations()
    for loc in locations:
        name_lower = loc.name.lower()
        id_lower = loc.location_id.lower()
        
        if loc.type == "mess":
            assert "girl" not in name_lower, f"Girls mess found in dataset: '{loc.name}'"
            assert "gh" not in name_lower.split(), f"Girls mess found in dataset: '{loc.name}'"
            assert "girl" not in id_lower, f"Girls mess found in dataset ID: '{loc.location_id}'"


def test_required_major_locations_exist(service: LocationService):
    """Test that all required major locations from the project specification exist."""
    required_ids = [
        "loc_main_gate",
        "loc_main_building",
        "loc_central_library",
        "loc_e_library",
        "loc_boys_coop",
        "loc_girls_coop",
        "loc_suprabha_boys",
        "loc_suprabha_girls",
        "loc_lhc_a",
        "loc_lhc_b",
    ]
    for loc_id in required_ids:
        loc = service.get_location_by_id(loc_id)
        assert loc is not None, f"Required major location '{loc_id}' is missing"


def test_boys_hostels_exist(service: LocationService):
    """Test that boys hostel blocks including Pushpagiri (Block 6) exist in the dataset."""
    boys_hostels = service.get_locations_by_type("hostel_boys")
    assert len(boys_hostels) >= 9, f"Expected at least 9 boys hostel blocks, found {len(boys_hostels)}"
    
    # Verify Pushpagiri (Block 6) exists
    pushpagiri = service.get_location_by_id("hostel_b_block6")
    assert pushpagiri is not None, "Block 6 (Pushpagiri) hostel is missing"
    assert pushpagiri.name == "Block 6 (Pushpagiri)"
    assert pushpagiri.campus == "EAST"

    # Verify Mega Towers exist
    mt_ids = ["hostel_b_mt1", "hostel_b_mt2", "hostel_b_mt3"]
    for mt_id in mt_ids:
        loc = service.get_location_by_id(mt_id)
        assert loc is not None, f"Boys Mega Tower '{mt_id}' is missing"


def test_girls_hostels_exist(service: LocationService):
    """Test that girls hostel blocks exist in the dataset."""
    girls_hostels = service.get_locations_by_type("hostel_girls")
    assert len(girls_hostels) >= 4, f"Expected at least 4 girls hostel blocks, found {len(girls_hostels)}"
    
    # Verify GH blocks exist
    gh_ids = ["hostel_g_gh1", "hostel_g_gh2", "hostel_g_gh3", "hostel_g_gh4"]
    for gh_id in gh_ids:
        loc = service.get_location_by_id(gh_id)
        assert loc is not None, f"Girls Hostel block '{gh_id}' is missing"


def test_official_mess_locations_exist(service: LocationService):
    """Test that all 11 official NITK mess locations from the 2025 Mess Location Chart exist."""
    expected_messes = [
        ("mess_gb", "GB Mess"),
        ("mess_pg_new_brahmagiri", "PG-New Brahmagiri"),
        ("mess_pg_pushpagiri", "PG-Pushpagiri"),
        ("mess_b1_karavali", "B1: Karavali"),
        ("mess_b2_aravali", "B2: Aravali"),
        ("mess_b3_vindhya", "B3: Vindhya"),
        ("mess_b4_satpura", "B4: Satpura"),
        ("mess_b5_nilgiri", "B5: Nilgiri"),
        ("mess_b7_sahyadri", "B7: Sahyadri"),
        ("mess_b8_trishul", "B8: Trishul"),
        ("mess_mega", "Mega Mess"),
    ]
    messes = service.get_locations_by_type("mess")
    assert len(messes) == 11, f"Expected exactly 11 official mess locations, found {len(messes)}"

    for mess_id, mess_name in expected_messes:
        loc = service.get_location_by_id(mess_id)
        assert loc is not None, f"Official mess '{mess_id}' ({mess_name}) is missing"
        assert loc.name == mess_name, f"Expected mess name '{mess_name}', got '{loc.name}'"
        assert loc.type == "mess"
        assert loc.campus == "EAST"


def test_deprecated_generic_mess_names_absent(service: LocationService):
    """Test that generic/unverified mess names are strictly absent from the dataset."""
    deprecated_names = [
        "central mess",
        "mega mess 1",
        "mega mess 2",
        "brahma mess",
        "campus food court",
    ]
    locations = service.get_all_locations()
    location_names = [loc.name.lower() for loc in locations]
    
    for dep_name in deprecated_names:
        assert dep_name not in location_names, f"Deprecated generic mess '{dep_name}' must not be present"


def test_demand_weights_validity(service: LocationService):
    """Test that all demand weights fall in the valid normalized range [0.0, 1.0]."""
    locations = service.get_all_locations()
    for loc in locations:
        for weight_name, weight_val in [
            ("peak_demand_weight", loc.peak_demand_weight),
            ("morning_demand_weight", loc.morning_demand_weight),
            ("lunch_demand_weight", loc.lunch_demand_weight),
            ("evening_demand_weight", loc.evening_demand_weight),
            ("night_demand_weight", loc.night_demand_weight),
        ]:
            assert 0.0 <= weight_val <= 1.0, (
                f"Location '{loc.location_id}' has out-of-range {weight_name}: {weight_val}"
            )


def test_pydantic_model_validation():
    """Test that Pydantic Location model enforces schema and raises ValidationError on invalid data."""
    # Invalid campus
    with pytest.raises(ValidationError):
        Location(
            location_id="test_1",
            name="Test Location",
            type="department",
            campus="NORTH",  # Invalid
            subzone="Test Zone",
            capacity=100,
            peak_demand_weight=0.5,
            morning_demand_weight=0.5,
            lunch_demand_weight=0.5,
            evening_demand_weight=0.5,
            night_demand_weight=0.5,
        )

    # Invalid demand weight (> 1.0)
    with pytest.raises(ValidationError):
        Location(
            location_id="test_2",
            name="Test Location",
            type="department",
            campus="EAST",
            subzone="Test Zone",
            capacity=100,
            peak_demand_weight=1.5,  # Invalid
            morning_demand_weight=0.5,
            lunch_demand_weight=0.5,
            evening_demand_weight=0.5,
            night_demand_weight=0.5,
        )

    # Invalid type
    with pytest.raises(ValidationError):
        Location(
            location_id="test_3",
            name="Test Location",
            type="invalid_type",  # Invalid
            campus="EAST",
            subzone="Test Zone",
            capacity=100,
            peak_demand_weight=0.5,
            morning_demand_weight=0.5,
            lunch_demand_weight=0.5,
            evening_demand_weight=0.5,
            night_demand_weight=0.5,
        )


def test_top_level_service_functions():
    """Test module-level convenience query functions."""
    all_locs = get_all_locations()
    assert len(all_locs) > 0
    
    cse = get_location_by_id("dept_cse")
    assert cse is not None
    assert cse.name == "Computer Science & Engineering"

    east_locs = get_locations_by_campus("EAST")
    west_locs = get_locations_by_campus("WEST")
    assert len(east_locs) + len(west_locs) == len(all_locs)

    mess_locs = get_locations_by_type("mess")
    assert len(mess_locs) == 11
    for m in mess_locs:
        assert m.type == "mess"

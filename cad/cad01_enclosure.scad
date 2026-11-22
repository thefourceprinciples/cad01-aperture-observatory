// ============================================================================
// CAD-01 Tabletop Metamaterial Testbed - Parametric Hardware Suite
// Fits: 75 mm ID / 85 mm OD Acrylic Tube + 88 mm Halo Flange + NEMA 17 + T8
// ============================================================================

// Select part to render & export as STL:
// "halo_flange"      -> Clamps acrylic tube, O-ring gasket, & Kagome plate (print 2)
// "kresling_carriage"-> Linear sliding stage driven by T8 nut & guide rods (print 1)
// "motor_mount"      -> Holds NEMA 17 stepper + 8mm linear guide rods (print 1)
// "transducer_cap"   -> Anechoic end-cap holding 16mm 40kHz piezo sensor (print 2)
PART_TO_RENDER = "halo_flange";

$fn = 96;

// --- Core Dimensions (mm) ---
tube_id         = 75.0;
tube_od         = 85.0;
flange_od       = 106.0;
bolt_circle_d   = 96.0;
m4_hole_d       = 4.3;
oring_groove_d  = 80.0;
oring_cord_d    = 2.5;

// --- Linear Stage & NEMA 17 Dimensions (mm) ---
rod_spacing     = 64.0;
rod_d           = 8.15;
t8_nut_flange_d = 22.0;
t8_nut_bore_d   = 10.4;
t8_bolt_circle  = 16.0;
nema17_width    = 42.3;
nema17_bolt_sp  = 31.0;
nema17_pilot_d  = 22.5;

// --- Transducer Dimensions (mm) ---
piezo_d         = 16.3;

module halo_flange() {
    flange_thick = 8.0;
    collar_h     = 14.0;

    difference() {
        union() {
            cylinder(d = flange_od, h = flange_thick);
            translate([0, 0, flange_thick])
                cylinder(d = tube_od + 6.0, h = collar_h);
        }
        translate([0, 0, -1])
            cylinder(d = tube_id, h = flange_thick + collar_h + 2);
        translate([0, 0, flange_thick])
            cylinder(d = tube_od + 0.3, h = collar_h + 1);
        translate([0, 0, 0])
            rotate_extrude()
                translate([oring_groove_d / 2, 0, 0])
                    circle(d = oring_cord_d);
        for (ang =) {
            rotate([0, 0, ang])
                translate([bolt_circle_d / 2, 0, -1])
                    cylinder(d = m4_hole_d, h = flange_thick + 2);
        }
    }
}

module kresling_carriage() {
    plate_thick = 10.0;
    ear_w       = 24.0;
    total_span  = rod_spacing + ear_w;

    difference() {
        union() {
            cylinder(d = flange_od, h = plate_thick);
            translate([-total_span / 2, -16, 0])
                cube([total_span, 32, plate_thick]);
            translate([0, flange_od / 2 + 12, 0])
                cylinder(d = 26, h = plate_thick);
        }
        translate([0, 0, -1])
            cylinder(d = tube_id, h = plate_thick + 2);
        for (ang =) {
            rotate([0, 0, ang])
                translate([bolt_circle_d / 2, 0, -1])
                    cylinder(d = m4_hole_d, h = plate_thick + 2);
        }
        for (sx = [-1, 1]) {
            translate([sx * (rod_spacing / 2), 0, -1])
                cylinder(d = rod_d, h = plate_thick + 2);
        }
        translate([0, flange_od / 2 + 12, -1]) {
            cylinder(d = t8_nut_bore_d, h = plate_thick + 2);
            for (ang =) {
                rotate([0, 0, ang])
                    translate([t8_bolt_circle / 2, 0, 0])
                        cylinder(d = 3.2, h = plate_thick + 2);
            }
        }
    }
}

module motor_mount() {
    wall_thick = 8.0;
    base_h     = 6.0;
    center_z   = 56.0;

    difference() {
        union() {
            translate([-55, -20, 0])
                cube([110, 40, base_h]);
            translate([-50, -wall_thick / 2, 0])
                cube([100, wall_thick, center_z + flange_od / 2 + 26]);
        }
        translate([0, 0, center_z])
            rotate([90, 0, 0])
                cylinder(d = tube_id, h = wall_thick + 4, center = true);
        for (sx = [-1, 1]) {
            translate([sx * (rod_spacing / 2), 0, center_z])
                rotate([90, 0, 0])
                    cylinder(d = 7.95, h = wall_thick + 4, center = true);
        }
        translate([0, 0, center_z + flange_od / 2 + 12]) {
            rotate([90, 0, 0])
                cylinder(d = nema17_pilot_d, h = wall_thick + 4, center = true);
            for (sx = [-1, 1], sz = [-1, 1]) {
                translate([sx * nema17_bolt_sp / 2, 0, sz * nema17_bolt_sp / 2])
                    rotate([90, 0, 0])
                        cylinder(d = 3.4, h = wall_thick + 4, center = true);
            }
        }
    }
}

module transducer_cap() {
    cap_depth  = 22.0;
    wall_thick = 4.0;

    difference() {
        cylinder(d = tube_od + 2 * wall_thick, h = cap_depth);
        translate([0, 0, wall_thick])
            cylinder(d = tube_od + 0.3, h = cap_depth);
        translate([0, 0, -1])
            cylinder(d = piezo_d, h = wall_thick + 2);
    }
}

if (PART_TO_RENDER == "halo_flange")       halo_flange();
if (PART_TO_RENDER == "kresling_carriage") kresling_carriage();
if (PART_TO_RENDER == "motor_mount")       motor_mount();
if (PART_TO_RENDER == "transducer_cap")    transducer_cap();

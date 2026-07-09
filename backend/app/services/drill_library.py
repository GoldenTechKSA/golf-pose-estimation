"""Curated practice drills, keyed by the metric they address.

The coaching model selects drill *ids* from this catalog; it never writes drill
text. A model-invented drill name ("the Hoganesque Lag Accelerator") is worse
than a generic one — it reads as authoritative and is unverifiable. Owning the
text here makes drills deterministic, reviewable, and testable, and shrinks the
model's job to the part it is actually good at: choosing which fault to name and
explaining why it matters.

Every id must be globally unique; `test_drill_library_integrity` enforces it.
"""
from typing import TypedDict


class Drill(TypedDict):
    id: str
    name: str
    fixes: str
    how_to: str


# Keys mirror the metric `key` values produced by metric_calculator._entry.
DRILLS: dict[str, list[Drill]] = {
    "tempo_ratio": [
        {
            "id": "tempo_metronome",
            "name": "Metronome 3:1",
            "fixes": "Grooves the roughly 3:1 backswing-to-downswing timing most tour players share.",
            "how_to": "Set a metronome to a slow, steady beat. Take the club back over three "
                      "beats and arrive at impact on the fourth. Hit nothing at first — just "
                      "swing to the beat until the rhythm stops feeling forced.",
        },
        {
            "id": "tempo_whoosh",
            "name": "Whoosh Drill",
            "fixes": "Cures a backswing that is rushed relative to the downswing.",
            "how_to": "Turn a club upside down and hold it by the head. Swing at full speed. "
                      "The loudest whoosh should happen at and just past the bottom, not early "
                      "in the downswing. If you hear it early, you are casting from the top.",
        },
    ],
    "shoulder_turn_at_top": [
        {
            "id": "turn_cross_arm",
            "name": "Crossed-Arm Turn",
            "fixes": "Builds a fuller shoulder turn without letting the arms lift to fake it.",
            "how_to": "Cross your arms over your chest, hands on opposite shoulders. Take your "
                      "address posture and turn back until your lead shoulder sits over your "
                      "trail foot. Hold for two seconds. Ten reps before you hit balls.",
        },
        {
            "id": "turn_back_to_target",
            "name": "Back-to-Target Check",
            "fixes": "Gives a simple feel for what a complete turn actually is.",
            "how_to": "Swing to the top and stop. Have someone standing down the line tell you "
                      "whether they can see your back. If they cannot, you have not finished "
                      "the turn — go a little further and stop again.",
        },
    ],
    "hip_turn_at_top": [
        {
            "id": "hip_chair_turn",
            "name": "Seated Hip Turn",
            "fixes": "Separates hip rotation from a lateral sway off the ball.",
            "how_to": "Sit on the front edge of a chair, club across your shoulders. Turn your "
                      "trail hip back and around without sliding sideways. You should feel the "
                      "trail glute load. Fifteen slow reps.",
        },
        {
            "id": "hip_trail_wall",
            "name": "Trail-Hip Wall",
            "fixes": "Stops the trail hip from sliding away from the target in the backswing.",
            "how_to": "Stand with your trail hip a few inches from a wall. Turn back. The hip "
                      "should rotate away, not bump into the wall. Contact means you swayed.",
        },
    ],
    "x_factor_at_top": [
        {
            "id": "xf_hips_quiet",
            "name": "Quiet-Hips Coil",
            "fixes": "Creates separation by letting the shoulders outrun the hips.",
            "how_to": "Make a normal backswing but consciously slow the hips to half the "
                      "shoulders' turn. You should feel a stretch across the trail side of the "
                      "torso at the top. That stretch is the separation.",
        },
        {
            "id": "xf_step_through",
            "name": "Step-Through Coil",
            "fixes": "Trains the feeling of loading the torso against a stable lower body.",
            "how_to": "Set up with feet together. Step your lead foot toward the target as you "
                      "start down. The step forces the lower body to lead and the torso to lag.",
        },
    ],
    "x_factor_stretch": [
        {
            "id": "xfs_pump",
            "name": "Transition Pump",
            "fixes": "Adds the small extra coil that happens as the hips start down before the shoulders.",
            "how_to": "Swing to the top. Pump the hips toward the target twice while keeping "
                      "your back turned, then swing through on the third. Feel the torso stretch "
                      "at each pump.",
        },
    ],
    "lead_arm_at_top": [
        {
            "id": "arm_towel_under",
            "name": "Towel Under the Arm",
            "fixes": "Keeps the lead arm connected and extended rather than collapsing at the top.",
            "how_to": "Tuck a small towel under your lead armpit. Make three-quarter swings "
                      "without dropping it. A collapsing lead arm lets the towel fall.",
        },
        {
            "id": "arm_width_check",
            "name": "Width Check at the Top",
            "fixes": "Restores swing width lost to a bent lead arm.",
            "how_to": "Swing to the top and stop. Look at your lead arm in a mirror or a phone "
                      "video. It should be straight or very nearly so. Reset and repeat until "
                      "straight feels normal.",
        },
    ],
    "lead_arm_at_impact": [
        {
            "id": "arm_impact_bag",
            "name": "Impact Bag",
            "fixes": "Trains a straight lead arm and forward shaft lean through the strike.",
            "how_to": "Swing slowly into an impact bag (or a stuffed duffel). Freeze on contact "
                      "and check that your lead arm and the club form one straight line, hands "
                      "ahead of the ball.",
        },
        {
            "id": "arm_release_extension",
            "name": "Two-Feet-Past Extension",
            "fixes": "Stops the arms folding immediately after impact.",
            "how_to": "Place a headcover two feet ahead of the ball on the target line. Swing "
                      "so the clubhead stays low and long enough to brush past it. Both arms "
                      "should be extended there.",
        },
    ],
    "spine_angle_at_address": [
        {
            "id": "spine_club_on_back",
            "name": "Club Along the Spine",
            "fixes": "Sets a neutral spine at address instead of slouching or over-arching.",
            "how_to": "Hold a club vertically against your back, touching your head, upper back, "
                      "and tailbone. Hinge from the hips until you reach address posture, keeping "
                      "all three contact points.",
        },
        {
            "id": "spine_hip_hinge",
            "name": "Hip Hinge to a Wall",
            "fixes": "Teaches bending from the hips rather than rounding the lower back.",
            "how_to": "Stand a foot from a wall, back turned. Push your rear back to touch the "
                      "wall while your chest lowers and your back stays flat. That is the hinge.",
        },
    ],
    "early_extension": [
        {
            "id": "ee_wall_butt",
            "name": "Butt-Against-the-Wall",
            "fixes": "Preserves the forward tilt you set at address instead of standing up into the ball.",
            "how_to": "Set up with your rear lightly touching a wall. Make slow half swings, "
                      "keeping contact through impact. Losing contact on the downswing is early "
                      "extension, and you will feel exactly when it happens.",
        },
        {
            "id": "ee_chair_behind",
            "name": "Chair Behind the Hip",
            "fixes": "Trains the trail hip to rotate back and around rather than thrust toward the ball.",
            "how_to": "Place a chair just behind your trail hip at address. Swing so the hip "
                      "rotates away from the chair on the way down. Bumping it means the hips "
                      "moved toward the ball.",
        },
        {
            "id": "ee_lead_glute",
            "name": "Lead-Glute Squeeze",
            "fixes": "Uses the posterior chain to hold posture through the strike.",
            "how_to": "From the top, start down by squeezing the lead glute and feeling the hips "
                      "rotate level. The chest stays over the ball rather than lifting.",
        },
    ],
    "head_stability": [
        {
            "id": "head_wall_touch",
            "name": "Head-Against-the-Wall",
            "fixes": "Quiets lateral head movement during the backswing.",
            "how_to": "Stand so the top of your head lightly touches a wall at address. Make "
                      "slow backswings keeping contact. Losing it means the head is sliding.",
        },
        {
            "id": "head_shadow",
            "name": "Shadow Drill",
            "fixes": "Gives instant feedback on head drop and lift with no equipment.",
            "how_to": "Practice with the sun behind you so your shadow falls in front. Watch the "
                      "shadow of your head as you swing — it should stay roughly still, not bob.",
        },
    ],
    "lead_knee_flex_at_address": [
        {
            "id": "knee_athletic_setup",
            "name": "Athletic Setup Check",
            "fixes": "Finds the flex that lets you rotate, between locked-straight and squatting.",
            "how_to": "Stand tall, then bend your knees until you feel your weight settle into "
                      "the middle of your feet and you could jump from there. That is the flex. "
                      "Check it in a mirror from face-on.",
        },
    ],
}


def drills_for(metric_key: str) -> list[Drill]:
    """Every drill catalogued for a metric. Empty when we have none."""
    return DRILLS.get(metric_key, [])


def valid_ids_for(metric_key: str) -> set[str]:
    return {d["id"] for d in drills_for(metric_key)}


def resolve(drill_id: str) -> Drill | None:
    for drills in DRILLS.values():
        for drill in drills:
            if drill["id"] == drill_id:
                return drill
    return None

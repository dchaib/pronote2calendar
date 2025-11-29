from pronote2calendar.subject_adjustments import apply_subject_adjustments


class DummySubject:
    """Mock subject object for testing"""

    def __init__(self, name):
        self.name = name


class DummyLesson:
    """Mock lesson object for testing"""

    def __init__(self, subject_name: str = "Math"):
        self.subject = DummySubject(subject_name)
        self.start = None
        self.end = None
        self.classroom = "Room 1"
        self.teacher_name = "Teacher"
        self.num = 1


def test_no_adjustments_returns_unchanged():
    """When no adjustments are configured, lessons should be unchanged"""
    lesson = DummyLesson("Physique-Chimie")

    result = apply_subject_adjustments([lesson], None)

    assert len(result) == 1
    assert result[0].subject.name == "Physique-Chimie"


def test_empty_subject_mapping_returns_unchanged():
    """When subject mapping is empty, lessons should be unchanged"""
    lesson = DummyLesson("Physique-Chimie")

    result = apply_subject_adjustments([lesson], {})

    assert len(result) == 1
    assert result[0].subject.name == "Physique-Chimie"


def test_adjust_single_subject():
    """Adjust a single subject name"""
    lesson = DummyLesson("Physique-Chimie")

    adjustments = {"Physique-Chimie": "Physique"}

    result = apply_subject_adjustments([lesson], adjustments)

    assert result[0].subject.name == "Physique"


def test_no_adjustment_when_subject_not_in_mapping():
    """No adjustment when subject is not in the mapping"""
    lesson = DummyLesson("Français")

    adjustments = {
        "Physique-Chimie": "Physique",
        "SVT": "Sciences de la Vie et de la Terre",
    }

    result = apply_subject_adjustments([lesson], adjustments)

    assert result[0].subject.name == "Français"


def test_multiple_subjects_adjusted():
    """All lessons with matching subjects should be adjusted"""
    lesson1 = DummyLesson("Physique-Chimie")
    lesson2 = DummyLesson("SVT")
    lesson3 = DummyLesson("Français")

    adjustments = {
        "Physique-Chimie": "Physique",
        "SVT": "Sciences de la Vie et de la Terre",
    }

    result = apply_subject_adjustments([lesson1, lesson2, lesson3], adjustments)

    assert len(result) == 3
    assert result[0].subject.name == "Physique"
    assert result[1].subject.name == "Sciences de la Vie et de la Terre"
    assert result[2].subject.name == "Français"


def test_many_subject_mappings():
    """Test with many subject mappings as per config"""
    lessons = [
        DummyLesson("Physique-Chimie"),
        DummyLesson("SVT"),
        DummyLesson("Histoire-Géographie"),
        DummyLesson("Vie de classe"),
        DummyLesson("Éducation musicale"),
        DummyLesson("Éducation physique et sportive"),
        DummyLesson("Français"),
    ]

    adjustments = {
        "Physique-Chimie": "Physique",
        "SVT": "Sciences de la Vie et de la Terre",
        "Histoire-Géographie": "Histoire-Géo",
        "Vie de classe": "Vie de Classe",
        "Éducation musicale": "Musique",
        "Éducation physique et sportive": "EPS",
    }

    result = apply_subject_adjustments(lessons, adjustments)

    assert len(result) == 7
    assert result[0].subject.name == "Physique"
    assert result[1].subject.name == "Sciences de la Vie et de la Terre"
    assert result[2].subject.name == "Histoire-Géo"
    assert result[3].subject.name == "Vie de Classe"
    assert result[4].subject.name == "Musique"
    assert result[5].subject.name == "EPS"
    assert result[6].subject.name == "Français"  # Not in mapping


def test_accent_handling():
    """Test that accented characters in subject names are handled correctly"""
    lesson = DummyLesson("Éducation physique et sportive")

    adjustments = {"Éducation physique et sportive": "EPS"}

    result = apply_subject_adjustments([lesson], adjustments)

    assert result[0].subject.name == "EPS"


def test_case_sensitive_matching():
    """Test that subject matching is case-sensitive"""
    lesson = DummyLesson("physique")

    adjustments = {"Physique": "Phys"}

    result = apply_subject_adjustments([lesson], adjustments)

    # Should not be adjusted because case is different
    assert result[0].subject.name == "physique"


def test_single_lesson():
    """Test adjustment with a single lesson"""
    lesson = DummyLesson("Math")

    adjustments = {"Math": "Mathématiques"}

    result = apply_subject_adjustments([lesson], adjustments)

    assert len(result) == 1
    assert result[0].subject.name == "Mathématiques"


def test_multiple_lessons_same_subject():
    """Test that all lessons with the same subject are adjusted"""
    lessons = [
        DummyLesson("Math"),
        DummyLesson("Math"),
        DummyLesson("Math"),
    ]

    adjustments = {"Math": "Mathématiques"}

    result = apply_subject_adjustments(lessons, adjustments)

    assert len(result) == 3
    for lesson in result:
        assert lesson.subject.name == "Mathématiques"


def test_preserves_other_lesson_properties():
    """Test that other lesson properties are preserved during adjustment"""
    lesson = DummyLesson("Physique-Chimie")
    lesson.classroom = "Room 101"
    lesson.teacher_name = "M. Dupont"
    lesson.num = 5

    adjustments = {"Physique-Chimie": "Physique"}

    result = apply_subject_adjustments([lesson], adjustments)

    assert result[0].subject.name == "Physique"
    assert result[0].classroom == "Room 101"
    assert result[0].teacher_name == "M. Dupont"
    assert result[0].num == 5


def test_empty_lessons_list():
    """Test that an empty lessons list is handled correctly"""
    adjustments = {"Math": "Mathématiques"}

    result = apply_subject_adjustments([], adjustments)

    assert result == []


def test_mixed_mapped_and_unmapped_subjects():
    """Test mix of mapped and unmapped subjects in a single operation"""
    lessons = [
        DummyLesson("Physique-Chimie"),
        DummyLesson("Français"),
        DummyLesson("SVT"),
        DummyLesson("English"),
    ]

    adjustments = {
        "Physique-Chimie": "Physique",
        "SVT": "Sciences",
    }

    result = apply_subject_adjustments(lessons, adjustments)

    assert result[0].subject.name == "Physique"  # Adjusted
    assert result[1].subject.name == "Français"  # Not in mapping
    assert result[2].subject.name == "Sciences"  # Adjusted
    assert result[3].subject.name == "English"  # Not in mapping


def test_subject_with_special_characters():
    """Test subject names with special characters"""
    lesson = DummyLesson("Histoire-Géographie")

    adjustments = {"Histoire-Géographie": "Histoire-Géo"}

    result = apply_subject_adjustments([lesson], adjustments)

    assert result[0].subject.name == "Histoire-Géo"


def test_subject_with_spaces():
    """Test subject names with spaces"""
    lesson = DummyLesson("Vie de classe")

    adjustments = {"Vie de classe": "Vie de Classe"}

    result = apply_subject_adjustments([lesson], adjustments)

    assert result[0].subject.name == "Vie de Classe"


def test_unicode_subject_names():
    """Test with various Unicode characters in subject names"""
    lessons = [
        DummyLesson("Français"),
        DummyLesson("Mathématiques"),
        DummyLesson("Éducation civique"),
    ]

    adjustments = {
        "Français": "FR",
        "Mathématiques": "MATH",
        "Éducation civique": "EC",
    }

    result = apply_subject_adjustments(lessons, adjustments)

    assert result[0].subject.name == "FR"
    assert result[1].subject.name == "MATH"
    assert result[2].subject.name == "EC"

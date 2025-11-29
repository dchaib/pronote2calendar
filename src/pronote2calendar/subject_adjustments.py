import logging

from pronotepy import Lesson

logger = logging.getLogger(__name__)


def apply_subject_adjustments(
    lessons: list[Lesson], adjustments_config: dict[str, str]
) -> list[Lesson]:
    if not adjustments_config:
        logger.debug("No subject adjustments configured")
        return lessons

    logger.debug("Applying subject adjustments to %d lessons", len(lessons))

    adjusted_lessons = []
    for lesson in lessons:
        adjusted_lesson = _adjust_lesson_subject(lesson, adjustments_config)
        adjusted_lessons.append(adjusted_lesson)

    return adjusted_lessons


def _adjust_lesson_subject(
    lesson: Lesson, adjustments_config: dict[str, str]
) -> Lesson:
    if lesson.subject is None:
        return lesson

    original_subject = lesson.subject.name

    if new_subject := adjustments_config.get(original_subject):
        lesson.subject.name = new_subject
        logger.debug(
            "Adjusted subject name from '%s' to '%s'",
            original_subject,
            new_subject,
        )

    return lesson

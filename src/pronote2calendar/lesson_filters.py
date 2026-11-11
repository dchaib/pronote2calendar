import logging

from pronotepy import Lesson

from pronote2calendar.settings import FiltersSettings

logger = logging.getLogger(__name__)


def filter_lessons(
    lessons: list[Lesson], filters_config: FiltersSettings
) -> list[Lesson]:
    excluded_subjects = set(filters_config.excluded_subjects)
    filtered_lessons = []
    for lesson in lessons:
        if lesson.subject is not None and lesson.subject.name in excluded_subjects:
            logger.debug(
                "Excluded lesson with subject '%s' starting at %s",
                lesson.subject.name,
                lesson.start,
            )
        else:
            filtered_lessons.append(lesson)

    logger.info(
        "Excluded %d of %d lessons by subject",
        len(lessons) - len(filtered_lessons),
        len(lessons),
    )
    return filtered_lessons

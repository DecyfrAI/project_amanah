import { LessonChoiceActivity } from './LessonChoiceActivity';
import { LessonPaperActivity } from './LessonPaperActivity';
import { LessonRoomActivity } from './LessonRoomActivity';
import { LessonSortActivity } from './LessonSortActivity';
import { LessonStageActivity } from './LessonStageActivity';
import {
  COEFFICIENT_ACTIVITY,
  INTERNET_ACTIVITY,
  MECHANISM_ACTIVITY,
  SCOPED_ACTIVITY,
} from './lesson-activities';

interface LessonActivityProps {
  moduleId: string;
}

/**
 * Dispatches the exercise for one syllabus module. Data is local.
 */
export function LessonActivity({ moduleId }: LessonActivityProps) {
  switch (moduleId) {
    case '01':
      return <LessonSortActivity />;
    case '02':
      return <LessonChoiceActivity activity={MECHANISM_ACTIVITY} />;
    case '03':
      return <LessonStageActivity />;
    case '04':
      return <LessonRoomActivity />;
    case '05':
      return <LessonChoiceActivity activity={INTERNET_ACTIVITY} />;
    case '06':
      return <LessonPaperActivity />;
    case '07':
      return <LessonChoiceActivity activity={COEFFICIENT_ACTIVITY} />;
    case '08':
      return <LessonChoiceActivity activity={SCOPED_ACTIVITY} />;
    default:
      return null;
  }
}

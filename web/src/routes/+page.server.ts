import { base } from '#lib/server/db.js';
import { resume } from '#lib/server/resume.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = () => ({ resume: resume(base()) });

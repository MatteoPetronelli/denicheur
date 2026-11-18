import { base } from '#lib/server/db.js';
import { stats } from '#lib/server/stats.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = () => ({ stats: stats(base()) });

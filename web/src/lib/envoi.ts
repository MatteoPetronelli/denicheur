import type { SubmitFunction } from '$app/forms';

/** `use:enhance={envoi}` : le bouton envoyeur est désactivé et marqué occupé jusqu'à la réponse. */
export const envoi: SubmitFunction = ({ submitter }) => {
	const bouton = submitter && 'disabled' in submitter ? (submitter as HTMLButtonElement) : null;
	bouton?.setAttribute('aria-busy', 'true');
	if (bouton) bouton.disabled = true;
	return async ({ update }) => {
		try {
			await update();
		} finally {
			bouton?.removeAttribute('aria-busy');
			if (bouton) bouton.disabled = false;
		}
	};
};

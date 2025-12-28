const createButton = document.getElementById('create-interaction');
const modal = document.getElementById('create-interaction-dialog');

// Open modal
if (createButton && modal) {
    createButton.addEventListener('click', () => {
        modal.showModal();
    });
}

// Close modal (button inside included content)
const closeModalButton = document.getElementById('close-modal');
if (closeModalButton && modal) {
    closeModalButton.addEventListener('click', () => {
        modal.close();
    });
}

// Expand modal to full page: collect current form values and navigate to a page
const expandModalButton = document.getElementById('expand-modal');
if (expandModalButton && modal) {
    expandModalButton.addEventListener('click', () => {
        const form = modal.querySelector('form');
        if (!form) {
            // Fallback: just go to create page
            window.location.href = '/interactions/create';
            return;
        }

        const params = new URLSearchParams();
        // collect named inputs
        const elements = form.elements;
        for (let i = 0; i < elements.length; i++) {
            const el = elements[i];
            if (!el.name) continue;
            // skip buttons
            if (el.type === 'button' || el.type === 'submit') continue;

            if (el.type === 'radio') {
                if (!el.checked) continue;
                params.set(el.name, el.value);
                continue;
            }

            if (el.tagName.toLowerCase() === 'select') {
                params.set(el.name, el.value);
                continue;
            }

            params.set(el.name, el.value);
        }

        const url = '/interactions/create' + (params.toString() ? ('?' + params.toString()) : '');
        // close modal then navigate
        try { modal.close(); } catch (e) {}
        window.location.href = url;
    });
}

// Submit form inside modal using ajax
const submitModalButton = document.getElementById('submit-create-interaction');
const successMessage = document.querySelector(".success-message")
if (submitModalButton) {
    submitModalButton.addEventListener('click', async (evt) => {
        evt.preventDefault()
        const form = document.getElementById("interaction-form");
        if (!form) {
            alert('Form not found.');
            return;
        }

        const formData = new FormData(form);
        const action = '/interactions/create';
        const method = 'PUT';

        try {
            const response = await fetch(action, {
                method: method,
                body: formData,
            });
            console.log(response);

            if (response.ok) {
                // Show success message
                if (successMessage) {
                    successMessage.classList.remove("hidden");
                }
                // Persist the notification and then reload so the message survives the reload
                if (window.persistNotification) {
                    window.persistNotification('success', 'Interaction créée avec succès !', 5000);
                }
                try { if (modal) modal.close(); } catch (e) {}
                window.location.reload(); // reload page; persisted notif will be shown on load
            } else {
                const errorCode = response.status;
                window.notify('error', `Erreur lors de la création de l'interaction (code ${errorCode})`, 10000);
            }
        } catch (error) {
            window.notify('error', "Erreur réseau lors de la création de l'interaction", 10000);
            console.error(error);
        }
    });
}

// Delete interaction button
const deleteButtons = document.getElementById("delete-interaction-button");
if (deleteButtons) {
    deleteButtons.addEventListener('click', async (evt) => {
        evt.preventDefault();
        if (!await window.confirmDialog({
            title: 'Confirmer la suppression',
            description: 'Êtes-vous sûr de vouloir supprimer cette interaction ? Cette action est irréversible.',
            confirmText: 'Supprimer',
            cancelText: 'Annuler',
            danger: true
        })) {
            return;
        }

        const id = deleteButtons.getAttribute('data-id');
        try {
            const response = await fetch(`/interactions/${id}/delete`, {
                method: 'DELETE',
            });
            if (response.ok) {
                // Persist a success notification and redirect to the interactions list
                if (window.notifyAndRedirect) {
                    window.notifyAndRedirect('success', 'Interaction supprimée avec succès !', 5000, '/interactions');
                } else {
                    // fallback
                    alert('Interaction supprimée avec succès !.');
                    window.location.href = '/interactions';
                }
            } else {
                const errorText = await response.text();
                alert('Une erreur est apparue pendant la suppression: ' + errorText);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    });
}

// Save the edit form using ajax
const saveEditButton = document.getElementById("edit-interaction-form");
if (saveEditButton) {
    saveEditButton.addEventListener('submit', async (evt) => {
        evt.preventDefault();
        const form = evt.target;
        const formData = new FormData(form);
        const action = window.location.href;
        const method = 'POST';

        try {
            const response = await fetch(action, {
                method: method,
                body: formData,
            });

            if (response.ok) {
                // Persist the notification and redirect to the view page so the message survives
                const redirectUrl = window.location.href.replace('/edit', '');
                if (window.notifyAndRedirect) {
                    window.notifyAndRedirect('success', 'Interaction enregistrée avec succès !', 5000, redirectUrl);
                } else {
                    window.persistNotification && window.persistNotification('success', 'Interaction enregistrée avec succès !', 5000);
                    window.location.href = redirectUrl;
                }
            } else {
                const errorCode = response.status;
                window.notify('error', `Erreur lors de l'enregistrement de l'interaction (code ${errorCode})`, 10000);
            }
        } catch (error) {
            window.notify('error', "Erreur réseau lors de l'enregistrement de l'interaction", 10000);
            console.error(error);
        }
    });
}
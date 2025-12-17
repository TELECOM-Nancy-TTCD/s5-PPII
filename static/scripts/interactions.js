const createButton = document.getElementById('create-interaction');
const modal = document.getElementById('create-interaction-dialog');

function clearFormErrors() {
    const els = document.querySelectorAll('.field-error');
    els.forEach(e => e.textContent = '');
    // remove invalid-field class from any previously marked inputs
    const invalids = document.querySelectorAll('.invalid-field');
    invalids.forEach(el => el.classList.remove('invalid-field'));

    // explicit clear for client search elements (in case hidden input was marked)
    const visibleClient = document.getElementById('client-search');
    const clientBox = document.getElementById('client-search-box');
    if (visibleClient) visibleClient.classList.remove('invalid-field');
    const clientTextInput = clientBox ? clientBox.querySelector('input[type="text"]') : null;
    if (clientTextInput) clientTextInput.classList.remove('invalid-field');
}

// trigger a shake animation on an element, removing the animation class after end
function triggerShake(el) {
    if (!el) return;
    // Remove existing to restart animation
    el.classList.remove('shake');
    // Force reflow to allow re-trigger
    // eslint-disable-next-line no-unused-expressions
    void el.offsetWidth;
    el.classList.add('shake');
    const handler = function() {
        el.classList.remove('shake');
        el.removeEventListener('animationend', handler);
    };
    el.addEventListener('animationend', handler);
}

function showFormErrors(errors) {
    // errors: { 'field-name': 'message' }
    // map server keys to element ids
    const mapping = {
        'type': 'error-type',
        'type_interaction': 'error-type',
        'interaction-date': 'error-interaction-date',
        'date_interaction': 'error-interaction-date',
        'client-id': 'error-client-id',
        'client_id': 'error-client-id',
        'title': 'error-title',
        'titre': 'error-title',
        'content': 'error-content',
        'contenu': 'error-content',
        'notes': 'error-content'
    };

    // mapping to input selectors for adding invalid class
    const inputSelector = {
        'type': '[name="type"]',
        'type_interaction': '[name="type"]',
        'interaction-date': '[name="interaction-date"]',
        'date_interaction': '[name="interaction-date"]',
        'client-id': '[name="client-id"]',
        'client_id': '[name="client-id"]',
        'title': '[name="title"]',
        'titre': '[name="title"]',
        'content': '[name="content"]',
        'contenu': '[name="content"]',
        'notes': '[name="content"]'
    };

    let any = false;
    let firstEl = null;
    for (const k in errors) {
        const id = mapping[k] || ('error-' + k);
        const el = document.getElementById(id);
        if (el) {
            el.textContent = errors[k];
            any = true;
        }
        // add invalid class to the related input if exists
        const sel = inputSelector[k] || '[name="' + k + '"]';
        const input = document.querySelector(sel);
        if (input) {
            input.classList.add('invalid-field');
            if (!firstEl) firstEl = input;
        }

        // Special case: the client field uses a hidden input for id and a visible #client-search for display
        if (k === 'client-id' || k === 'client_id') {
            const visibleClient = document.getElementById('client-search');
            const clientBox = document.getElementById('client-search-box');
            const clientTextInput = clientBox ? clientBox.querySelector('input[type="text"]') : null;
            // Add invalid class to multiple possible visible elements so the border is seen
            if (visibleClient) {
                visibleClient.classList.add('invalid-field');
                if (!firstEl) firstEl = visibleClient;
            }
            if (clientTextInput) {
                clientTextInput.classList.add('invalid-field');
                if (!firstEl) firstEl = clientTextInput;
            }
        }
    }
    // if no mapped errors, show alert as fallback
    if (!any) {
        alert(Object.values(errors).join('\n'));
    }
    // focus/scroll to first invalid field if present
    if (firstEl) {
        try { firstEl.focus(); } catch (e) {}
        firstEl.scrollIntoView({behavior: 'smooth', block: 'center'});
        // trigger a shake to draw attention
        triggerShake(firstEl);
    }
}

// Nouvelle validation côté client pour éviter d'envoyer des requêtes inutiles
function validateFormClientSide(form) {
    const errors = {};
    if (!form) return errors;

    // helper to read values from form or inputs
    const get = (names) => {
        for (const n of names) {
            // try form elements first
            const el = form.querySelector('[name="' + n + '"]');
            if (el) {
                return el.value;
            }
        }
        return '';
    };

    const clientId = get(['client-id', 'client_id', 'client']);
    if (!clientId || String(clientId).trim() === '') {
        errors['client-id'] = 'Le client est requis.';
    }

    const typeVal = get(['type', 'type_interaction']);
    if (!typeVal || String(typeVal).trim() === '' || String(typeVal).trim() === "Type") {
        errors['type'] = 'Le type d\'interaction est requis.';
    } else {
        // ensure the type exists among select options
        const select = form.querySelector('select[name="type"]');
        if (select) {
            const opt = Array.from(select.options).some(o => o.value === typeVal);
            if (!opt) errors['type'] = 'Type d\'interaction invalide.';
        }
    }

    const dateVal = get(['interaction-date', 'date_interaction', 'date']);
    if (!dateVal || String(dateVal).trim() === '') {
        errors['interaction-date'] = 'La date est requise.';
    } else {
        // Accept YYYY-MM-DD or YYYY-MM-DDTHH:MM
        const re = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?$/;
        if (!re.test(dateVal)) {
            errors['interaction-date'] = 'Format de date invalide. Utiliser YYYY-MM-DD ou YYYY-MM-DDTHH:MM.';
        } else {
            try {
                const now = new Date();
                if (dateVal.indexOf('T') >= 0) {
                    // datetime-local -> parse as local time
                    const d = new Date(dateVal);
                    if (isNaN(d.getTime())) {
                        errors['interaction-date'] = 'Format de date/heure invalide.';
                    } else if (d.getTime() > now.getTime()) {
                        errors['interaction-date'] = 'La date/heure ne peut pas être supérieure à la date actuelle.';
                    }
                } else {
                    // date-only: compare by date (ignore time)
                    const parts = dateVal.split('-').map(p => parseInt(p, 10));
                    if (parts.length !== 3 || parts.some(isNaN)) {
                        errors['interaction-date'] = 'Format de date invalide.';
                    } else {
                        const d = new Date(parts[0], parts[1] - 1, parts[2]);
                        // zero time for comparison
                        d.setHours(0,0,0,0);
                        const today = new Date();
                        today.setHours(0,0,0,0);
                        if (d.getTime() > today.getTime()) {
                            errors['interaction-date'] = 'La date ne peut pas être supérieure à la date du jour.';
                        }
                    }
                }
            } catch (e) {
                errors['interaction-date'] = 'Erreur lors de la validation de la date.';
            }
        }
    }

    const title = get(['title', 'titre']);
    if (!title || String(title).trim() === '') {
        errors['title'] = 'Le titre est requis.';
    }

    const content = get(['content', 'contenu', 'notes']);
    if (!content || String(content).trim() === '') {
        errors['content'] = 'Le contenu est requis.';
    }

    return errors;
}

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

        clearFormErrors();

        // Validation côté client avant d'envoyer
        const clientSideErrors = validateFormClientSide(form);
        if (Object.keys(clientSideErrors).length) {
            showFormErrors(clientSideErrors);
            return;
        }

        const formData = new FormData(form);
        // Validation minimale côté client (redondant mais conservé)
        const clientId = formData.get('client-id');
        if (!clientId) {
            showFormErrors({'client-id': 'Veuillez sélectionner un client.'});
            return;
        }

        const action = '/interactions/create';
        const method = 'PUT';

        try {
            const response = await fetch(action, {
                method: method,
                body: formData,
                credentials: 'same-origin'
            });
            //console.log(response);

            if (response.ok) {
                // Show success message
                if (successMessage) {
                    successMessage.classList.remove("hidden");
                }
                // If it's a modal, close it after 5s and refresh the page
                setTimeout(() => {
                    if (modal) try { modal.close(); } catch (e) {}
                    window.location.reload(); // or update the UI as needed
                }, 5000);
            } else if (response.status === 400) {
                const data = await response.json();
                if (data && data.errors) {
                    showFormErrors(data.errors);
                } else {
                    const text = await response.text();
                    alert('Error: ' + text);
                }
            } else {
                const errorText = await response.text();
                alert('Error submitting form: ' + errorText);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    });
}

// Delete interaction button
const deleteButtons = document.getElementById("delete-interaction");
if (deleteButtons) {
    deleteButtons.addEventListener('click', async (evt) => {
        evt.preventDefault();
        if (!confirm('Êtes-vous sûr de vouloir supprimer cette interaction ?')) {
            return;
        }

        const id = deleteButtons.getAttribute('data-id');
        try {
            const response = await fetch(`/interactions/${id}/delete`, {
                method: 'DELETE',
                credentials: 'same-origin'
            });
            if (response.ok) {
                alert('Interaction supprimée avec succès !.');
                window.location.href = '/interactions';
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
        clearFormErrors();
        const form = evt.target;

        // Validation côté client avant d'envoyer
        const clientSideErrors = validateFormClientSide(form);
        if (Object.keys(clientSideErrors).length) {
            showFormErrors(clientSideErrors);
            return;
        }

        const formData = new FormData(form);
        const action = window.location.href;
        const method = 'POST';

        try {
            const response = await fetch(action, {
                method: method,
                body: formData,
                credentials: 'same-origin'
            });

            if (response.ok) {
                alert('Interaction modifiée avec succès.');
                window.location.href = window.location.href.replace('/edit', '');
            } else if (response.status === 400) {
                const data = await response.json();
                if (data && data.errors) {
                    showFormErrors(data.errors);
                } else {
                    const text = await response.text();
                    alert('Error: ' + text);
                }
            } else {
                const errorText = await response.text();
                alert("Une erreur est apparue durant l'enregistrement: " + errorText);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    });
}
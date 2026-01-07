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
    const handler = function () {
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
        try {
            firstEl.focus();
        } catch (e) {
        }
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
                        d.setHours(0, 0, 0, 0);
                        const today = new Date();
                        today.setHours(0, 0, 0, 0);
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
        try {
            modal.close();
        } catch (e) {
        }
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
        // Validation minimale côté client
        const clientId = formData.get('client-id');
        if (!clientId) {
            showFormErrors({'client-id': 'Veuillez sélectionner un client.'});
            return;
        }

        const action = '/interactions/create';
        const method = 'PUT';

        try {
            const response = await fetch(action, {
                method: method, body: formData,
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
                try {
                    if (modal) modal.close();
                } catch (e) {
                }
                window.location.reload(); // reload page; persisted notif will be shown on load

            } else if (response.status === 400) {
                const data = await response.json();
                if (data && data.errors) {
                    showFormErrors(data.errors);
                } else {
                    const text = await response.text();
                    alert('Error: ' + text);
                }
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
const deleteButtons = document.getElementById("delete-interaction");
if (deleteButtons) {
    deleteButtons.addEventListener('submit', async (evt) => {
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
                method: method, body: formData,
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
            } else if (response.status === 400) {
                const data = await response.json();
                if (data && data.errors) {
                    showFormErrors(data.errors);
                } else {
                    const text = await response.text();
                    alert('Error: ' + text);
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

/* Pagination interactive: transforme le centre en champ texte pour sélectionner une page */
(function () {
    try {
        const pag = document.getElementById('pagination');
        if (!pag) return;
        const current = parseInt(pag.getAttribute('data-current') || '0', 10);
        const lastAttr = pag.getAttribute('data-last');
        const last = lastAttr === '' ? null : parseInt(lastAttr, 10);
        const q = encodeURIComponent(pag.getAttribute('data-q') || '');
        const ordt = encodeURIComponent(pag.getAttribute('data-ord-t') || '');
        const ord = encodeURIComponent(pag.getAttribute('data-ord') || 'asc');
        const l = encodeURIComponent(pag.getAttribute('data-l') || '10');

        const center = document.getElementById('page-center');
        const prev = document.getElementById('pag-prev');
        const next = document.getElementById('pag-next');
        const lastBtn = pag.querySelector('.last-page');

        function buildHref(p) {
            return `?q=${q}&l=${l}&ord-t=${ordt}&ord=${ord}&p=${p}`;
        }

        // Compute final disabled states first
        const firstBtn = pag.querySelector('.first-page');
        const shouldDisablePrev = current <= 0;
        const shouldDisableNext = (last !== null) ? (current >= last) : false;
        const shouldDisableFirst = current === 0;
        const shouldDisableLast = (last === null) || (current === last);

        // Apply classes/aria/tabindex according to final states
        if (firstBtn) {
            const isAnchor = firstBtn.tagName === 'A';
            if (shouldDisableFirst) {
                firstBtn.classList.add('disabled');
                firstBtn.setAttribute('aria-disabled', 'true');
                if (isAnchor) {
                    firstBtn.removeAttribute('href');
                    firstBtn.setAttribute('tabindex', '-1');
                } else {
                    firstBtn.disabled = true;
                    firstBtn.setAttribute('tabindex', '-1');
                }
            } else {
                firstBtn.classList.remove('disabled');
                firstBtn.removeAttribute('aria-disabled');
                firstBtn.removeAttribute('tabindex');
                if (isAnchor) {
                    firstBtn.href = buildHref(0);
                } else {
                    firstBtn.disabled = false;
                }
            }
        }

        if (prev) {
            const isAnchor = prev.tagName === 'A';
            if (shouldDisablePrev) {
                prev.classList.add('disabled');
                prev.setAttribute('aria-disabled', 'true');
                if (isAnchor) {
                    prev.removeAttribute('href');
                    prev.setAttribute('tabindex', '-1');
                } else {
                    prev.disabled = true;
                    prev.setAttribute('tabindex', '-1');
                }
            } else {
                prev.classList.remove('disabled');
                prev.removeAttribute('aria-disabled');
                prev.removeAttribute('tabindex');
                if (isAnchor) {
                    prev.href = buildHref(Math.max(0, current - 1));
                } else {
                    prev.disabled = false;
                }
            }
        }

        if (next) {
            const isAnchor = next.tagName === 'A';
            if (shouldDisableNext) {
                next.classList.add('disabled');
                next.setAttribute('aria-disabled', 'true');
                if (isAnchor) {
                    next.removeAttribute('href');
                    next.setAttribute('tabindex', '-1');
                } else {
                    next.disabled = true;
                    next.setAttribute('tabindex', '-1');
                }
            } else {
                next.classList.remove('disabled');
                next.removeAttribute('aria-disabled');
                next.removeAttribute('tabindex');
                if (isAnchor) {
                    next.href = buildHref((last !== null) ? Math.min(last, current + 1) : (current + 1));
                } else {
                    next.disabled = false;
                }
            }
        }

        if (lastBtn) {
            const isAnchor = lastBtn.tagName === 'A';
            if (last === null) {
                lastBtn.classList.add('disabled');
                lastBtn.setAttribute('aria-disabled', 'true');
                if (isAnchor) {
                    lastBtn.removeAttribute('href');
                    lastBtn.setAttribute('tabindex', '-1');
                } else {
                    lastBtn.disabled = true;
                    lastBtn.setAttribute('tabindex', '-1');
                }
                // add title for screen readers
                lastBtn.setAttribute('title', `Dernière`);
                lastBtn.setAttribute('aria-label', `Dernière`);
            } else {
                // set title/aria-label with page number; do not replace inner icon
                lastBtn.setAttribute('title', `Dernière (${last + 1})`);
                lastBtn.setAttribute('aria-label', `Dernière (${last + 1})`);
                if (shouldDisableLast) {
                    lastBtn.classList.add('disabled');
                    lastBtn.setAttribute('aria-disabled', 'true');
                    if (isAnchor) {
                        lastBtn.removeAttribute('href');
                        lastBtn.setAttribute('tabindex', '-1');
                    } else {
                        lastBtn.disabled = true;
                        lastBtn.setAttribute('tabindex', '-1');
                    }
                } else {
                    lastBtn.classList.remove('disabled');
                    lastBtn.removeAttribute('aria-disabled');
                    lastBtn.removeAttribute('tabindex');
                    if (isAnchor) {
                        lastBtn.href = buildHref(last);
                    } else {
                        lastBtn.disabled = false;
                    }
                }
            }
        }

        // Also ensure any anchor elements that still have the 'disabled' class cannot be activated
        const disabledAnchors = pag.querySelectorAll('a.disabled');
        disabledAnchors.forEach(a => {
            // remove href if present
            if (a.hasAttribute('href')) a.removeAttribute('href');
            // ensure not focusable
            a.setAttribute('tabindex', '-1');
            // avoid adding multiple listeners
            if (!a.dataset.disabledListener) {
                a.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); }, { capture: true });
                a.dataset.disabledListener = '1';
            }
        });

        // Block clicks on any anchor with class 'disabled' as a final safeguard
        pag.addEventListener('click', function (e) {
            const a = e.target.closest('a');
            if (!a) return;
            if (a.classList.contains('disabled') || a.getAttribute('aria-disabled') === 'true') {
                e.preventDefault();
                e.stopPropagation();
                return;
            }
        }, { capture: true });

        if (!center) return;
        // When clicking the center element, replace it by a small form with an input
        center.addEventListener('click', function (evt) {
            evt.preventDefault();
            const parentLi = center.parentElement;
            if (!parentLi) return;
            // create form
            const form = document.createElement('form');
            form.style.display = 'inline';
            form.style.margin = '0';
            form.className = 'inline-page-form';
            const input = document.createElement('input');
            input.type = 'number';
            input.min = '1';
            if (last !== null) input.max = String(last + 1);
            input.value = String(current + 1);
            input.style.width = '70px';
            input.style.padding = '6px';
            input.style.borderRadius = '6px';
            input.style.border = '1px solid rgba(255,255,255,0.08)';
            input.autofocus = true;
            input.className = 'page-input';

            // append only the input (no Go button)
            form.appendChild(input);

            // Replace center link with form
            parentLi.replaceChild(form, center);

            // handle cancel and submit logic
            let submitted = false;
            const cancel = () => {
                // restore original center link
                if (parentLi.contains(form)) {
                    parentLi.replaceChild(center, form);
                }
            };

            const submitAction = () => {
                if (submitted) return;
                const v = parseInt(input.value, 10);
                if (isNaN(v) || v < 1) {
                    input.classList.add('invalid-field');
                    try { input.focus(); } catch (e) {}
                    return;
                }
                let targetPage = v - 1; // convert to 0-based
                if (last !== null && targetPage > last) targetPage = last;
                submitted = true;
                // navigate
                window.location.href = buildHref(targetPage);
            };

            // Escape to cancel
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    cancel();
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    submitAction();
                }
            });

            // On blur, submit (after short timeout to allow potential focus changes)
            input.addEventListener('blur', () => setTimeout(() => { if (document.activeElement !== input) submitAction(); }, 150));

            // remove any lingering listeners for a submit button (none created now)
        });
    } catch (e) {
        console.error('Pagination script error', e);
    }
})();

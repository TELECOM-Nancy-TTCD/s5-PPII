// Gestionnaire de la page Rôles: selection, édition, toggles, re-order
// Champs de permissions connus (doivent correspondre à Role.FIELD_NAMES côté serveur)
const PERMISSION_FIELDS = [
    'administrateur',
    'peut_gerer_utilisateurs', 'peut_gerer_roles',
    'peut_lire_clients', 'peut_gerer_clients',
    'peut_creer_interactions', 'peut_gerer_interactions',
    'peut_lire_projets', 'peut_gerer_projets', 'peut_gerer_jalons', 'peut_assigner_intervenants',
    'peut_lire_intervenants', 'peut_modifier_intervenants', 'peut_acceder_documents', 'peut_gerer_competences',
    'peut_lancer_matching', 'peut_exporter_csv'
];

function qs(sel, el = document) {
    return el.querySelector(sel);
}

function qsa(sel, el = document) {
    return Array.from(el.querySelectorAll(sel));
}

// Load initial roles into a mapping (id -> element)
const rolesListEl = qs('#roles-list');
let roleElements = qsa('.role-item');
let selectedRoleId = null;

// Snapshot + debounce state for reorder + rollback
let lastOrderSnapshot = null; // array of role ids before a drag started
let reorderDebounceTimer = null;
let pendingReorderIds = null;
let reorderPromises = [];
const REORDER_DEBOUNCE_MS = 350;

function showEmptyMessage() {
    const empty = qs('#empty-message');
    const form = qs('#role-form');
    if (empty) empty.style.display = ''; form.classList.remove("hidden");
    if (form) form.style.display = 'none'; form.classList.add("hidden");
}

function showForm() {
    const empty = qs('#empty-message');
    const form = qs('#role-form');
    if (empty) empty.style.display = 'none'; form.classList.add("hidden");
    if (form) form.classList.remove("hidden"), form.style.display = '';
}

function clearSelection() {
    roleElements.forEach(e => e.classList.remove('selected'));
    selectedRoleId = null;
    const form = qs('#role-form');
    if (form) form.reset();
    const perms = qs('#permissions-list');
    if (perms) perms.innerHTML = '';
    const title = qs('#detail-title');
    if (title) title.textContent = 'Détails du rôle';
    showEmptyMessage();
}

function loadRoleToForm(roleObj, pushHistory = true) {
    // roleObj is an object containing role fields
    if (!roleObj) {
        clearSelection();
        return;
    }
    selectedRoleId = roleObj.role_id;
    roleElements = qsa('.role-item');
    roleElements.forEach(e => e.classList.toggle('selected', Number(e.dataset.roleId) === Number(selectedRoleId)));

    qs('#role_id').value = roleObj.role_id;
    qs('#role_nom').value = roleObj.nom || '';
    qs('#role_hierarchie').value = roleObj.hierarchie ?? '';
    qs('#detail-title').textContent = `Rôle : ${roleObj.nom || ''}`;

    // build permissions checkboxes only if not already server-rendered
    const pl = qs('#permissions-list');
    const existingInputs = pl && pl.querySelectorAll('input[type="checkbox"]').length > 0;
    if (!existingInputs) {
        pl.innerHTML = '';
        PERMISSION_FIELDS.forEach(f => {
            const val = !!roleObj[f];
            const id = `perm-${f}`;
            const wrapper = document.createElement('label');
            wrapper.className = 'checkbox-con';
            wrapper.style.display = 'flex';
            wrapper.style.alignItems = 'center';
            wrapper.style.gap = '8px';
            wrapper.innerHTML = `<input type="checkbox" id="${id}" name="${f}" ${val ? 'checked' : ''}>` + `<span style="font-size:14px; margin-left:10px; color:var(--text-light)">${f}</span>`;
            const row = document.createElement('div');
            row.className = 'permission-row';
            row.appendChild(wrapper);
            pl.appendChild(row);
        });
    } else {
        // If server-rendered, just update the checkbox checked state according to roleObj
        PERMISSION_FIELDS.forEach(f => {
            const cb = qs(`#perm-${f}`);
            if (cb) cb.checked = !!roleObj[f];
        });
    }

    showForm();

    // update URL to reflect selection
    if (pushHistory) {
        const newUrl = `/utilisateurs/roles/${roleObj.role_id}`;
        try {
            history.pushState({roleId: roleObj.role_id}, '', newUrl);
        } catch (e) {
        }
    }

    // Apply form state (disable fields/permissions if needed)
    try {
        applyFormState(roleObj);
    } catch (e) {/* ignore */
    }
}

// fetch role details from server
async function fetchRoleDetails(roleId) {
    try {
        const res = await fetch(`/api/utilisateurs/roles/${roleId}`);
        if (!res.ok) {
            // try to parse returned body for an error message (JSON or text)
            let bodyText;
            try {
                bodyText = await res.text();
            } catch (_) {
                bodyText = '';
            }
            let msg = `Erreur chargement rôle (${res.status})`;
            try {
                const parsed = JSON.parse(bodyText);
                if (parsed && parsed.error) msg = parsed.error;
            } catch (_) {
                if (bodyText) msg = bodyText;
            }
            // notify user
            window.notify && window.notify('error', msg, 6000);
            console.error('Erreur chargement rôle', res.status, bodyText);
            return null;
        }
        const data = await res.json();
        return data.role;
    } catch (e) {
        window.notify && window.notify('error', "Erreur réseau lors du chargement du rôle", 5000);
        console.error('Impossible de charger le rôle : ' + e.message);
        return null;
    }
}

// helper: select role element by id
function selectRoleElementById(id) {
    return qs(`.role-item[data-role-id="${id}"]`);
}

// helper: update hierarchy values displayed in the list and in the form
function applyHierarchyToList(order) {
    // order: array of role_id in DOM order (top -> bottom)
    if (!Array.isArray(order)) return;
    order.forEach((roleId, idx) => {
        const el = selectRoleElementById(roleId);
        if (!el) return;
        // update data attribute
        el.dataset.hierarchie = idx;
        // update visible meta if present
        const meta = el.querySelector('.role-meta');
        if (meta) meta.textContent = `Hiérarchie: ${idx}`;
        // if this role is currently selected, update the form input
        if (Number(selectedRoleId) === Number(roleId)) {
            const hierField = qs('#role_hierarchie');
            if (hierField) hierField.value = idx;
        }
        // mark as disabled/no-drop if this role is above or equal to the current user's position
        try {
            const numericIdx = Number(idx);
            if (typeof userHier === 'number' && !isNaN(userHier)) {
                if (numericIdx <= Number(userHier)) {
                    el.classList.add('role-disabled');
                    el.classList.add('no-drop');
                } else {
                    el.classList.remove('role-disabled');
                    el.classList.remove('no-drop');
                }
            }
        } catch (e) {
            // ignore
        }
    });
}

// helper: build role DOM element from role object
function buildRoleElement(roleObj) {
    const wrapper = document.createElement('div');
    wrapper.className = 'role-item card-utilisateurs';
    wrapper.setAttribute('draggable', 'true');
    wrapper.dataset.roleId = roleObj.role_id;
    wrapper.dataset.hierarchie = roleObj.hierarchie ?? '';
    const isDisabled = (userHier !== null && roleObj.hierarchie !== null && Number(roleObj.hierarchie) < Number(userHier));
    if (isDisabled) wrapper.classList.add('role-disabled');
    wrapper.innerHTML = `
    <div class="role-item-inner">
      <a class="role-link" href="/utilisateurs/roles/${roleObj.role_id}">
        <div class="role-main">
          <div class="role-name">${escapeHtml(roleObj.nom || '')}</div>
          <div class="role-meta">Hiérarchie: ${roleObj.hierarchie ?? ''}</div>
          ${isDisabled ? '<div class="role-lock" title="Rôle protégé"><i class="fa-solid fa-lock"></i></div>' : ''}
        </div>
      </a>
      <div class="role-drag-handle right">
        <button class="order-button" aria-label="Déplacer"><i class="fa-solid fa-grip-lines"></i></button>
      </div>
    </div>
  `;
    return wrapper;
}

// simple escaper for inserted text
function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>"']/g, function (m) {
        return ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": "&#39;"})[m];
    });
}


async function doSendReorder(idsToSend) {
    if (!Array.isArray(idsToSend)) return false;
    try {
        const res = await fetch('/api/utilisateurs/roles/reorder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({order: idsToSend})
        });
        if (!res.ok) {
            let bodyText;
            try {
                bodyText = await res.text();
            } catch (_) {
                bodyText = '';
            }
            let msg = bodyText || ('HTTP ' + res.status);
            try {
                const parsed = JSON.parse(bodyText);
                if (parsed && parsed.error) msg = parsed.error;
            } catch (_) {
            }
            window.notify && window.notify('error', 'Erreur enregistrement ordre : ' + msg, 5000);
            // rollback to last snapshot if available
            if (lastOrderSnapshot && Array.isArray(lastOrderSnapshot)) {
                const list = qs('#roles-list');
                const map = {};
                roleElements.forEach(el => {
                    map[Number(el.dataset.roleId)] = el;
                });
                list.innerHTML = '';
                lastOrderSnapshot.forEach(id => {
                    if (map[id]) list.appendChild(map[id]);
                });
                applyHierarchyToList(lastOrderSnapshot);
            }
            return false;
        }

        // success: apply new order in UI, clear snapshot, notify
        applyHierarchyToList(idsToSend);
        lastOrderSnapshot = null;
        window.notify && window.notify('success', 'Ordre des rôles enregistré', 3000);
        return true;
    } catch (e) {
        console.error('Erreur sendReorder:', e);
        window.notify && window.notify('error', "Erreur réseau lors de l'enregistrement de l'ordre", 5000);
        if (lastOrderSnapshot && Array.isArray(lastOrderSnapshot)) {
            const list = qs('#roles-list');
            const map = {};
            roleElements.forEach(el => {
                map[Number(el.dataset.roleId)] = el;
            });
            list.innerHTML = '';
            lastOrderSnapshot.forEach(id => {
                if (map[id]) list.appendChild(map[id]);
            });
            applyHierarchyToList(lastOrderSnapshot);
        }
        return false;
    }
}

function sendReorder(ids) {
    if (!Array.isArray(ids)) return Promise.resolve(false);
    pendingReorderIds = Array.from(ids);

    return new Promise((resolve, reject) => {
        reorderPromises.push({resolve, reject});
        if (reorderDebounceTimer) clearTimeout(reorderDebounceTimer);
        reorderDebounceTimer = setTimeout(async () => {
            reorderDebounceTimer = null;
            const idsToSend = pendingReorderIds;
            pendingReorderIds = null;
            try {
                const ok = await doSendReorder(idsToSend);
                reorderPromises.forEach(p => p.resolve(ok));
                reorderPromises = [];
            } catch (err) {
                reorderPromises.forEach(p => p.reject(err));
                reorderPromises = [];
            }
        }, REORDER_DEBOUNCE_MS);
    });
}


// insert role into the DOM list (at end or at position based on hierarchie)
function insertRoleIntoList(roleObj, select = true) {
    // if role with same id exists, replace it
    const existing = selectRoleElementById(roleObj.role_id);
    if (existing) {
        // update name/meta
        const name = existing.querySelector('.role-name');
        if (name) name.textContent = roleObj.nom || '';
        const meta = existing.querySelector('.role-meta');
        if (meta) meta.textContent = `Hiérarchie: ${roleObj.hierarchie ?? ''}`;
        if (select) loadRoleToForm(roleObj);
        return existing;
    }

    const el = buildRoleElement(roleObj);
    // place according to hierarchie if available
    const list = qs('#roles-list');
    let placed = false;
    if (roleObj.hierarchie !== null && roleObj.hierarchie !== undefined) {
        const items = qsa('.role-item');
        for (const it of items) {
            const itmHier = it.dataset.hierarchie !== undefined ? Number(it.dataset.hierarchie) : null;
            if (itmHier !== null && itmHier > Number(roleObj.hierarchie)) {
                it.parentNode.insertBefore(el, it);
                placed = true;
                break;
            }
        }
    }
    if (!placed) list.appendChild(el);
    // refresh cached roleElements
    roleElements = qsa('.role-item');
    // Ensure the newly inserted element has handlers (drag, pointer, anchors not draggable)
    try {
        attachDragHandlers(el);
        preventAnchorDrag();
    } catch (_) {
    }
    // optionally select it
    if (select) {
        loadRoleToForm(roleObj);
        try {
            history.pushState({roleId: roleObj.role_id}, '', `/utilisateurs/roles/${roleObj.role_id}`);
        } catch (e) {
        }
        // apply form state for newly selected role
        try {
            applyFormState(roleObj);
        } catch (e) {
        }
    }
    return el;
}

// attach create handler to all create buttons (duplicate id in template)
qsa('[id="create-role-btn"]').forEach(btn => {
    btn.addEventListener('click', async () => {
        // if form has unsaved changes, confirm first
        if (formChanged) {
            const ok = await window.showConfirm({
                title: 'Modifications non enregistrées',
                description: 'Vous avez des modifications non sauvegardées. Voulez-vous créer un nouveau rôle sans sauvegarder ?',
                confirmText: 'Continuer',
                cancelText: 'Annuler',
                danger: false
            });
            if (!ok) return;
        }

        const defaultName = 'Nouveau rôle';
        const payload = {nom: defaultName};
        try {
            // send PUT as requested
            const res = await fetch('/api/utilisateurs/roles', {
                method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
            });
            if (!res.ok) {
                const t = await res.text();
                window.notify && window.notify("error", "Un erreur est survenue lors de la création du rôle", 5000);
                console.error('Erreur création : ' + t);
                return;
            }
            const data = await res.json();
            const role = data.role;
            const rolesList = data.roles || null;
            if (!role || !role.role_id) {
                window.notify("error", 'Création OK mais réponse invalide');
                return;
            }
            // update full list if provided (safer), otherwise insert the single role
            if (Array.isArray(rolesList) && rolesList.length > 0) {
                // rebuild list DOM
                const list = qs('#roles-list');
                list.innerHTML = '';
                rolesList.forEach(r => {
                    const el = buildRoleElement(r);
                    el.dataset.hierarchie = r.hierarchie ?? '';
                    list.appendChild(el);
                });
                roleElements = qsa('.role-item');
                // attach handlers to rebuilt items
                try {
                    attachHandlersToAll();
                } catch (_) {
                }
                // select the created
                const newEl = selectRoleElementById(role.role_id) || insertRoleIntoList(role, false);
                if (newEl) {
                    newEl.classList.add('selected');
                }
            } else {
                insertRoleIntoList(role, true);
            }
            // clear dirty flag and navigate to the detail URL
            formChanged = false;
            window.location.href = `/utilisateurs/roles/${role.role_id}`;
        } catch (err) {
            window.notify("error", "Erreur réseau lors de la création du rôle", 5000);
            console.error('Erreur réseau lors de la création : ' + err.message);
        }
    });
});

qsa('.create-role-secondary').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        e.preventDefault();
        // delegate to the main create button handler by dispatching a click on the first create-role-btn
        const main = document.querySelector('#create-role-btn');
        if (main) main.click();
    });
});

// track whether the form has unsaved changes
let formChanged = false;
const roleForm = qs('#role-form');
if (roleForm) {
    roleForm.addEventListener('input', () => {
        formChanged = true;
    });
    roleForm.addEventListener('change', () => {
        formChanged = true;
    });
}

// Helper: return current user permissions object (same logic as applyFormState)
function getCurrentUserPermissions() {
    if (window.currentUserPermissions && typeof window.currentUserPermissions === 'object') return window.currentUserPermissions;
    if (window.serverRoles && Array.isArray(window.serverRoles) && window.currentUserRoleId) {
        return window.serverRoles.find(r => Number(r.role_id) === Number(window.currentUserRoleId)) || null;
    }
    return null;
}

// Helper: decide if the current user can edit the given role object
function canEditRole(roleObj) {
    try {
        if (!roleObj) return false;
        // Cannot edit own role
        if (window.currentUserRoleId && Number(window.currentUserRoleId) === Number(roleObj.role_id)) return false;
        if (typeof userHier === 'number' && roleObj.hierarchie !== undefined && roleObj.hierarchie !== null) {
            if (Number(roleObj.hierarchie) <= Number(userHier)) return false;
        }
        // If we have explicit permissions, require manage roles or administrator
        const perms = getCurrentUserPermissions();
        if (perms) {
            if (perms.administrateur) return true;
            if (perms.peut_gerer_roles) return true;
            return false;
        }
        // If we don't have permission info, be permissive and allow editing (server will enforce)
        return true;
    } catch (e) {
        return false;
    }
}

// intercept clicks on role links to warn about unsaved changes and load via AJAX
if (rolesListEl) {
    rolesListEl.addEventListener('click', async (e) => {
        const link = e.target.closest && e.target.closest('.role-link');
        if (!link) return;
        // If this link is within a disabled role, ignore click
        const roleItem = link.closest('.role-item');
        if (roleItem && roleItem.classList.contains('role-disabled')) {
            e.preventDefault();
            return; // do nothing
        }
        e.preventDefault();
        const item = link.closest('.role-item');
        if (!item) return;
        const roleId = item.dataset.roleId;
        if (!roleId) return;

        // if form has unsaved changes, ask confirmation
        if (formChanged) {
            const ok = await window.showConfirm({
                title: 'Modifications non enregistrées',
                description: 'Vous avez des modifications non sauvegardées. Voulez-vous continuer sans sauvegarder ?',
                confirmText: 'Continuer',
                cancelText: 'Annuler',
                danger: false
            });
            if (!ok) return;
        }

        // fetch role details
        const role = await fetchRoleDetails(roleId);
        if (!role) return;

        // Only display the modification form if the current user is allowed to edit this role
        if (canEditRole(role)) {
            loadRoleToForm(role);
            formChanged = false;
        } else {
            window.notify && window.notify('error', "Vous n'avez pas les droits pour modifier ce rôle.", 5000);
            // Optionally show read-only info: showEmptyMessage() keeps form hidden
            // We keep selection visual but do not open the edit form
            roleElements = qsa('.role-item');
            roleElements.forEach(e => e.classList.toggle('selected', Number(e.dataset.roleId) === Number(role.role_id)));
        }
    });
}

// Save logic factored to a function so both the form submit and the save button call it
async function saveRole() {
    const roleId = qs('#role_id') && qs('#role_id').value;
    const nomEl = qs('#role_nom');
    if (!roleId || !nomEl) {
        window.notify && window.notify('error', 'Aucun rôle sélectionné.', 5000);
        console.error("Impossible de sauvegarder : role_id ou nom manquant");
        return;
    }

    // Prevent saving if user is editing their own role
    if (window.currentUserRoleId && Number(window.currentUserRoleId) === Number(roleId)) {
        window.notify && window.notify('error', 'Vous ne pouvez pas modifier votre propre rôle.', 5000);
        return;
    }

    const payload = {nom: (nomEl.value || '').trim()};
    PERMISSION_FIELDS.forEach(f => {
        const cb = qs(`#perm-${f}`);
        if (cb) payload[f] = cb.checked ? 1 : 0;
    });
    try {
        const res = await fetch(`/api/utilisateurs/roles/${roleId}`, {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const t = await res.json();
            if (t && t.error) {
                window.notify && window.notify("error", 'Erreur sauvegarde : ' + t.error);
            }
            console.log('Erreur sauvegarde : ', t);
            return;
        }
        const data = await res.json();
        const role = data.role;
        if (!role || !role.role_id) {
            window.notify && window.notify("error", 'Sauvegarde OK mais réponse invalide');
            return;
        }
        // update role in list
        insertRoleIntoList(role, true);
        window.notify && window.notify('success', 'Rôle sauvegardé', 3000);
        formChanged = false;
    } catch (err) {
        window.notify && window.notify("error", "Erreur réseau lors de la sauvegarde du rôle", 5000);
        console.error('Erreur réseau lors de la sauvegarde : ', err);
    }
}

// attach saveRole to form submit if form exists
const roleFormEl = qs('#role-form');
if (roleFormEl) {
    roleFormEl.addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveRole();
    });
}

// wire the save button to the same save logic
const saveBtn = qs('#save-role');
if (saveBtn) {
    saveBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        await saveRole();
    });
}

// warn when navigating away from the page with unsaved changes
window.addEventListener('beforeunload', (e) => {
    if (formChanged) {
        e.preventDefault();
        e.returnValue = '';
        return '';
    }
});

const deleteBtnEl = qs('#delete-role');
if (deleteBtnEl) {
    deleteBtnEl.addEventListener('click', async () => {
        const roleId = qs('#role_id').value;
        if (!roleId) {
            window.notify && window.notify('error', 'Aucun rôle sélectionné.', 5000);
            return;
        }
        if (!await window.showConfirm({
            title: 'Supprimer le rôle',
            description: 'Voulez-vous vraiment supprimer ce rôle ? Cette action est irréversible.',
            confirmText: 'Supprimer',
            cancelText: 'Annuler',
            danger: true
        })) return;
        try {
            const res = await fetch(`/api/utilisateurs/roles/${roleId}/delete`, {method: 'DELETE'});
            if (res.ok) {
                window.notify && window.notify('success', 'Rôle supprimé', 3000);
                const el = selectRoleElementById(roleId);
                if (el) el.remove();
                clearSelection();
            } else {
                const txt = await res.text();
                window.notify("error", "Erreur suppression du rôle", 5000);
                console.error('Erreur suppression : ' + txt);
            }
        } catch (e) {
            window.notify("error", "Erreur réseau lors de la suppression du rôle", 5000);
            console.error('Erreur réseau lors de la suppression : ' + e.message);
        }
    });
}

let dragged = null;
if (rolesListEl) {
    rolesListEl.addEventListener('dragstart', (e) => {
        const item = e.target.closest('.role-item');
        if (!item) {
            e.preventDefault();
            return;
        }
        // snapshot before any DOM movement
        try {
            lastOrderSnapshot = qsa('.role-item').map(el => Number(el.dataset.roleId));
        } catch (_) {
            lastOrderSnapshot = null;
        }

        // if the item is marked role-disabled (i.e. higher than current user), prevent dragging
        if (item.classList.contains('role-disabled')) {
            e.preventDefault();
            window.notify && window.notify('error', 'Vous ne pouvez pas déplacer un rôle supérieur au vôtre', 4000);
            return;
        }
        dragged = item;
        e.dataTransfer.effectAllowed = 'move';
        item.style.opacity = '0.5';
    });
    rolesListEl.addEventListener('dragend', async (_e) => {
        if (dragged) dragged.style.opacity = '';
        console.debug('dragend');
        // clear flags on all items
        qsa('.role-item').forEach(i => delete i.dataset.dragAllowed);
        // After drag end, collect new order and send to server
        const ids = qsa('.role-item').map(el => Number(el.dataset.roleId));
        dragged = null;
        try {
            await sendReorder(ids);
        } catch (e) {
            console.error(e);
        }
    });
    rolesListEl.addEventListener('dragover', (e) => {
        e.preventDefault();
        const over = e.target.closest('.role-item');
        if (!over || over === dragged) return;
        const rect = over.getBoundingClientRect();
        const after = (e.clientY - rect.top) > rect.height / 2;

        // determine insertion index if we were to insert here
        const items = Array.from(rolesListEl.querySelectorAll('.role-item')).filter(i => i !== dragged);
        const overIndex = items.indexOf(over);
        const insertionIndex = overIndex + (after ? 1 : 0);

        // UI-level prevention: compute current user's index from snapshot (fallback to server-sent userHier)
        const currentIdx = getCurrentUserIndexFromSnapshot();
        if (currentIdx !== null && insertionIndex <= Number(currentIdx)) {
            over.classList.add('no-drop');
            notifyNoDropOnce(over, 'Vous ne pouvez pas placer un rôle au-dessus de votre rôle.');
            setTimeout(() => over.classList.remove('no-drop'), 500);
            return; // do not move
        }

        // If userHier defined (legacy fallback), prevent insertion into protected zone (indices <= userHier)
        if (userHier !== null && userHier !== undefined) {
            if (insertionIndex <= Number(userHier)) {
                over.classList.add('no-drop');
                notifyNoDropOnce(over, 'Vous ne pouvez pas placer un rôle au-dessus de votre rôle.');
                setTimeout(() => over.classList.remove('no-drop'), 500);
                return; // do not move
            }
        }

        if (after) over.parentNode.insertBefore(dragged, over.nextSibling);
        else over.parentNode.insertBefore(dragged, over);
    });
}

// Update touchmove to enforce insertion rules on mobile
(function enableTouchReorder() {
    if (!rolesListEl) return; // nothing to do without the list
    let touchDragging = null;
    // candidate starts as object {item, startX, startY, activated}
    let touchCandidate = null;
    const ACTIVATION_THRESHOLD = 8; // pixels

    rolesListEl.addEventListener('touchstart', (e) => {
        const t = e.touches && e.touches[0];
        if (!t) return;
        const elAtPoint = document.elementFromPoint(t.clientX, t.clientY);
        const item = elAtPoint && elAtPoint.closest ? elAtPoint.closest('.role-item') : null;
        if (!item) return;
        // do not activate dragging yet — wait for movement to distinguish tap vs drag
        touchCandidate = {item: item, startX: t.clientX, startY: t.clientY, activated: false};
        // keep passive true until we actually activate (avoid blocking scroll on simple taps)
    }, {passive: true});

    rolesListEl.addEventListener('touchmove', (e) => {
        const t = e.touches && e.touches[0];
        if (!t) return;
        // If we have no candidate, nothing to do
        if (!touchCandidate) return;

        // If not yet activated, check movement distance
        if (!touchCandidate.activated) {
            const dx = Math.abs(t.clientX - touchCandidate.startX);
            const dy = Math.abs(t.clientY - touchCandidate.startY);
            if (Math.max(dx, dy) < ACTIVATION_THRESHOLD) {
                // not considered a drag yet
                return;
            }
            // activate drag
            touchCandidate.activated = true;
            touchDragging = touchCandidate.item;
            try {
                lastOrderSnapshot = qsa('.role-item').map(el => Number(el.dataset.roleId));
            } catch (_) {
                lastOrderSnapshot = null;
            }

            dragged = touchDragging; // reuse global dragged so other logic can see it
            touchDragging.style.opacity = '0.5';
            touchDragging.classList.add('dragging-touch');
            // now prevent scrolling for the active drag
            e.preventDefault();
        }

        // If activated, proceed with reposition logic
        if (touchCandidate.activated && touchDragging) {
            const el = document.elementFromPoint(t.clientX, t.clientY);
            const over = el && el.closest ? el.closest('.role-item') : null;
            if (!over || over === touchDragging) return;
            const rect = over.getBoundingClientRect();
            const after = (t.clientY - rect.top) > rect.height / 2;

            // determine insertion index if we were to insert here
            const items = Array.from(rolesListEl.querySelectorAll('.role-item')).filter(i => i !== dragged);
            const overIndex = items.indexOf(over);
            const insertionIndex = overIndex + (after ? 1 : 0);

            // UI-level prevention: compute current user's index from snapshot (fallback to server-sent userHier)
            const currentIdx = getCurrentUserIndexFromSnapshot();
            if (currentIdx !== null && insertionIndex <= Number(currentIdx)) {
                over.classList.add('no-drop');
                notifyNoDropOnce(over, 'Vous ne pouvez pas placer un rôle au-dessus de votre rôle.');
                setTimeout(() => over.classList.remove('no-drop'), 500);
                return; // do not move
            }

            // If userHier defined (legacy fallback), prevent insertion into protected zone (indices <= userHier)
            if (userHier !== null && userHier !== undefined) {
                if (insertionIndex <= Number(userHier)) {
                    over.classList.add('no-drop');
                    notifyNoDropOnce(over, 'Vous ne pouvez pas placer un rôle au-dessus de votre rôle.');
                    setTimeout(() => over.classList.remove('no-drop'), 500);
                    return; // do not move
                }
            }

            if (after) over.parentNode.insertBefore(touchDragging, over.nextSibling);
            else over.parentNode.insertBefore(touchDragging, over);
            // prevent scrolling while dragging
            e.preventDefault();
        }
    }, {passive: false});

    async function finishTouchDrag() {
        if (!touchDragging) return;
        touchDragging.style.opacity = '';
        touchDragging.classList.remove('dragging-touch');
        // clear flags on all items
        qsa('.role-item').forEach(i => delete i.dataset.dragAllowed);
        // collect new order and send to server (reuse same endpoint as desktop dragend)
        const ids = qsa('.role-item').map(el => Number(el.dataset.roleId));
        try {
            await sendReorder(ids);
        } catch (e) {
            console.error(e);
        }

        dragged = null;
        touchDragging = null;
        touchCandidate = null;
    }

    rolesListEl.addEventListener('touchend', () => {
        // if we never activated dragging, it's a tap — let normal click handlers run
        if (touchCandidate && touchCandidate.activated) {
            finishTouchDrag().then(() => {
            });
        }
        touchCandidate = null;
    });
    rolesListEl.addEventListener('touchcancel', () => {
        if (touchCandidate && touchCandidate.activated) {
            finishTouchDrag().then(() => {
            });
        }
        touchCandidate = null;
    });
})();

(async () => {
    try {
        // If server injected the full role object, use it (avoids an extra fetch)
        if (window.serverRole) {
            loadRoleToForm(window.serverRole, false);
            try {
                applyFormState(window.serverRole);
            } catch (e) {
            }
            return;
        }

        const maybe = window.initialRoleId || null;
        if (maybe) {
            const role = await fetchRoleDetails(maybe);
            if (role) {
                loadRoleToForm(role, false);
                try {
                    applyFormState(role);
                } catch (e) {
                }
                return;
            }
        }
        // default: select first role if any
        /*roleElements = qsa('.role-item');
        if(roleElements.length > 0){
          const firstId = roleElements[0].dataset.roleId;
          const first = await fetchRoleDetails(firstId);
          if(first) loadRoleToForm(first, false);
        } else {*/
        showEmptyMessage();
        //}
    } catch (e) {
        console.error('Erreur initialisation roles page', e);
        showEmptyMessage();
    }
})();

// handle back/forward navigation
window.addEventListener('popstate', async (_ev) => {
    const state = (history && history.state) || {};
    const roleId = state.roleId;
    if (roleId) {
        const role = await fetchRoleDetails(roleId);
        if (role) loadRoleToForm(role, false);
    } else {
        showEmptyMessage();
    }
});

// read current user info exposed by the server (ensure defined)
const userHier = (typeof window.currentUserHier === 'number' && !isNaN(window.currentUserHier)) ? Number(window.currentUserHier) : (window.currentUserHier ? Number(window.currentUserHier) : null);

// Prevent anchors inside role items from being drag sources
function preventAnchorDrag() {
    qsa('.role-item a.role-link').forEach(a => {
        a.setAttribute('draggable', 'false');
    });
}

// Attach drag handlers to a role-item element (used for dynamically created items)
function attachDragHandlers(item) {
    if (!item) return;
    // ensure draggable on the container
    item.setAttribute('draggable', 'true');
    item.addEventListener('dragstart', (e) => {
        // snapshot before any DOM movement
        try {
            lastOrderSnapshot = qsa('.role-item').map(el => Number(el.dataset.roleId));
        } catch (_) {
            lastOrderSnapshot = null;
        }

        if (item.classList.contains('role-disabled')) {
            e.preventDefault();
            return;
        }
        console.debug('dragstart', item.dataset.roleId);
        dragged = item;
        e.dataTransfer.effectAllowed = 'move';
        try {
            e.dataTransfer.setData('text/plain', item.dataset.roleId);
        } catch (_) {
        }
        item.style.opacity = '0.5';
    });
    item.addEventListener('dragend', async () => {
        if (item) item.style.opacity = '';
        // clear flags
        qsa('.role-item').forEach(i => delete i.dataset.dragAllowed);
        const ids = qsa('.role-item').map(el => Number(el.dataset.roleId));
        dragged = null;
        try {
            await sendReorder(ids);
        } catch (e) {
            console.error(e);
        }
    });

    // pointer-based drag fallback for better reliability across browsers/devices
    let pointerDragState = {startX: 0, startY: 0, activated: false, dragged: null, placeholder: null};
    item.addEventListener('pointerdown', (ev) => {
        // only start for primary button/touch
        if (!ev.isPrimary || (ev.button !== 0 && ev.pointerType === 'mouse')) return;
        // ignore if clicking on interactive controls (inputs, buttons)
        const targetTag = ev.target && ev.target.tagName ? ev.target.tagName.toLowerCase() : '';
        if (['input', 'textarea', 'select', 'label'].includes(targetTag)) return;
        if (item.classList.contains('role-disabled')) return;

        // record start position and prepare to detect a drag gesture
        pointerDragState.startX = ev.clientX;
        pointerDragState.startY = ev.clientY;
        pointerDragState.activated = false;
        pointerDragState.dragged = item;

        const THRESHOLD = 6; // pixels before we treat movement as a drag

        function onPointerMove(e) {
            const dx = Math.abs(e.clientX - pointerDragState.startX);
            const dy = Math.abs(e.clientY - pointerDragState.startY);
            if (!pointerDragState.activated) {
                if (Math.max(dx, dy) < THRESHOLD) return; // not yet a drag
                // activate custom drag
                pointerDragState.activated = true;
                // snapshot before DOM movement
                try {
                    lastOrderSnapshot = qsa('.role-item').map(el => Number(el.dataset.roleId));
                } catch (_) {
                    lastOrderSnapshot = null;
                }

                item.classList.add('dragging-custom');
                const ph = document.createElement('div');
                ph.className = 'role-placeholder';
                ph.style.height = `${item.getBoundingClientRect().height}px`;
                item.parentNode.insertBefore(ph, item.nextSibling);
                pointerDragState.placeholder = ph;
                try {
                    item.setPointerCapture(ev.pointerId);
                } catch (_) {
                }
                // dim item visually
                item.style.opacity = '0.5';
                e.preventDefault();
            }

            if (pointerDragState.activated) {
                const draggedEl = pointerDragState.dragged;
                const elUnder = document.elementFromPoint(e.clientX, e.clientY);
                const over = elUnder && elUnder.closest ? elUnder.closest('.role-item') : null;
                if (!over || over === draggedEl || over === pointerDragState.placeholder) return;
                const rect = over.getBoundingClientRect();
                const after = (e.clientY - rect.top) > rect.height / 2;

                // determine insertion index and enforce userHier rules
                const items = Array.from(rolesListEl.querySelectorAll('.role-item')).filter(i => i !== draggedEl);
                const overIndex = items.indexOf(over);
                const insertionIndex = overIndex + (after ? 1 : 0);

                // UI-level prevention using snapshot (fallback to userHier)
                const currentIdx = getCurrentUserIndexFromSnapshot();
                if (currentIdx !== null && insertionIndex <= Number(currentIdx)) {
                    over.classList.add('no-drop');
                    notifyNoDropOnce(over, 'Vous ne pouvez pas placer un rôle au-dessus de votre rôle.');
                    setTimeout(() => over.classList.remove('no-drop'), 300);
                    return;
                }

                // legacy fallback
                if (userHier !== null && userHier !== undefined && insertionIndex <= Number(userHier)) {
                    over.classList.add('no-drop');
                    notifyNoDropOnce(over, 'Vous ne pouvez pas placer un rôle au-dessus de votre rôle.');
                    setTimeout(() => over.classList.remove('no-drop'), 300);
                    return;
                }

                if (after) {
                    over.parentNode.insertBefore(draggedEl, over.nextSibling);
                    over.parentNode.insertBefore(pointerDragState.placeholder, draggedEl.nextSibling);
                } else {
                    over.parentNode.insertBefore(draggedEl, over);
                    over.parentNode.insertBefore(pointerDragState.placeholder, draggedEl.nextSibling);
                }
                e.preventDefault();
            }
        }

        function onPointerUp() {
            document.removeEventListener('pointermove', onPointerMove);
            document.removeEventListener('pointerup', onPointerUp);
            if (!pointerDragState.activated) {
                // it was a tap, not our custom drag
                pointerDragState.dragged = null;
                pointerDragState.placeholder = null;
                pointerDragState.activated = false;
                return;
            }
            // finish custom drag
            try {
                item.releasePointerCapture(ev.pointerId);
            } catch (_) {
            }
            item.classList.remove('dragging-custom');
            if (pointerDragState.placeholder) {
                pointerDragState.placeholder.remove();
            }
            item.style.opacity = '';
            const ids = qsa('.role-item').map(el => Number(el.dataset.roleId));
            sendReorder(ids).catch(e => console.error(e));

            pointerDragState.dragged = null;
            pointerDragState.placeholder = null;
            pointerDragState.activated = false;
        }

        document.addEventListener('pointermove', onPointerMove);
        document.addEventListener('pointerup', onPointerUp);
    });

    // ensure anchors inside item are not draggable
    const anchor = item.querySelector('a.role-link');
    if (anchor) anchor.setAttribute('draggable', 'false');
}

// Attach handlers to all existing items
function attachHandlersToAll() {
    preventAnchorDrag();
    qsa('.role-item').forEach(it => attachDragHandlers(it));
}

// Call on init
attachHandlersToAll();

// Determine current user's index in the lastOrderSnapshot (if available) or fallback to userHier
function getCurrentUserIndexFromSnapshot() {
    try {
        if (Array.isArray(lastOrderSnapshot) && window.currentUserRoleId) {
            const id = Number(window.currentUserRoleId);
            const idx = lastOrderSnapshot.indexOf(id);
            return idx >= 0 ? idx : null;
        }
        // fallback: use userHier if it's a numeric index
        if (typeof userHier === 'number' && !isNaN(userHier)) return Number(userHier);
    } catch (e) {
        return null;
    }
    return null;
}

// Notify an element once to avoid spamming notifications while dragging
function notifyNoDropOnce(el, message) {
    try {
        if (!el) return;
        if (el.dataset && el.dataset._noDropNotified) return;
        el.dataset._noDropNotified = '1';
        window.notify && window.notify('error', message, 2500);
        setTimeout(() => {
            try {
                delete el.dataset._noDropNotified;
            } catch (_) {
            }
        }, 1200);
    } catch (e) {
        // ignore
    }
}

// Apply form state: disable permissions that the current user cannot modify
function applyFormState(_roleObj) {
    try {
        const permContainer = qs('#permissions-list');
        if (!permContainer) return;

        // Determine current user's permission set. Prefer explicit injection
        let curPerms = null;
        if (window.currentUserPermissions && typeof window.currentUserPermissions === 'object') {
            curPerms = window.currentUserPermissions;
        } else if (window.serverRoles && Array.isArray(window.serverRoles) && window.currentUserRoleId) {
            const myRole = window.serverRoles.find(r => Number(r.role_id) === Number(window.currentUserRoleId));
            if (myRole) curPerms = myRole;
        }

        // If no info, assume full control (do nothing)
        if (!curPerms) return;

        // For each permission field, decide if current user can modify it:
        // rule: user can only toggle permissions that they themselves possess (curPerms[field] truthy)
        PERMISSION_FIELDS.forEach(field => {
            const input = qs(`#perm-${field}`);
            const row = input ? input.closest('.permission-row') : null;
            const allowed = !!curPerms[field];
            if (!allowed) {
                if (row) {
                    row.classList.add('perm-locked');
                    row.title = 'Vous ne pouvez pas modifier cette permission.';
                }
                if (input) {
                    input.disabled = true;
                    input.setAttribute('aria-disabled', 'true');
                }
            } else {
                if (row) {
                    row.classList.remove('perm-locked');
                    row.removeAttribute('title');
                }
                if (input) {
                    input.disabled = false;
                    input.removeAttribute('aria-disabled');
                }
            }
        });

        // Additionally, disable role name editing if user cannot manage roles
        const canManageRoles = !!(curPerms && (curPerms.peut_gerer_roles || curPerms.administrateur));
        const nameField = qs('#role_nom');
        if (nameField) {
            nameField.disabled = !canManageRoles;
            if (!canManageRoles) {
                nameField.classList.add('perm-locked');
                nameField.title = 'Vous ne pouvez pas modifier le nom de ce rôle.';
            } else {
                nameField.classList.remove('perm-locked');
                nameField.removeAttribute('title');
            }
        }

        const saveBtn = qs('#save-role');
        if (saveBtn) saveBtn.disabled = !canManageRoles;

    } catch (e) {
        console.error('applyFormState error', e);
    }
}

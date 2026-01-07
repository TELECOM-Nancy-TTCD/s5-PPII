// Script to show the confirmation <dialog id="confirm"> present in templates/menu.html
// Usage:
// showConfirm({ title: 'Supprimer', description: 'Voulez-vous ... ?', confirmText: 'Supprimer', cancelText: 'Annuler' })
//   .then(confirmed => { if (confirmed) { /* user confirmed */ } });

(function () {
    'use strict';

    function findDialog() {
        return document.getElementById('confirm');
    }

    function showConfirm(options = {}) {
        const dialog = findDialog();
        if (!dialog) {
            console.warn('confirm dialog element (#confirm) not found');
            return Promise.resolve(false);
        }

        const titleEl = dialog.querySelector('#confirm-title');
        const descEl = dialog.querySelector('#confirm-description');
        const btnCancel = dialog.querySelector('#confirm-cancel');
        const btnConfirm = dialog.querySelector('#confirm-delete-button');

        const opts = Object.assign({
            title: titleEl ? titleEl.textContent : 'Confirmer',
            description: descEl ? descEl.textContent : '',
            confirmText: btnConfirm ? btnConfirm.textContent : 'Confirmer',
            cancelText: btnCancel ? btnCancel.textContent : 'Annuler',
            danger: false // can be used to add a danger class or style
        }, options || {});

        if (titleEl) titleEl.textContent = opts.title;
        if (descEl) descEl.textContent = opts.description;
        if (btnConfirm) btnConfirm.textContent = opts.confirmText;
        if (btnCancel) btnCancel.textContent = opts.cancelText;

        // toggle danger class if requested
        if (opts.danger) {
            btnConfirm.classList.add('danger-button');
        } else if (btnConfirm) {
            btnConfirm.classList.remove('danger-button');
            btnConfirm.classList.add('primary-button');
        }

        // Ensure any previous handlers are removed before adding new ones
        const cleanupListeners = [];

        return new Promise((resolve) => {
            function done(result) {
                // remove listeners
                cleanupListeners.forEach(({el, type, handler}) => el.removeEventListener(type, handler));
                // small delay to allow dialog close animation if any
                try { if (dialog.open) dialog.close(); } catch (e) { /* ignore */ }
                resolve(result);
            }

            // confirm handler
            const onConfirm = function (e) {
                e.preventDefault();
                done(true);
            };

            const onCancel = function (e) {
                e.preventDefault();
                done(false);
            };

            const onKey = function (e) {
                if (e.key === 'Escape') {
                    // close on escape
                    done(false);
                }
            };

            // click outside dialog to cancel (backdrop)
            const onBackdropClick = function (e) {
                if (e.target === dialog) {
                    done(false);
                }
            };

            // attach listeners
            if (btnConfirm) { btnConfirm.addEventListener('click', onConfirm); cleanupListeners.push({el: btnConfirm, type: 'click', handler: onConfirm}); }
            if (btnCancel) { btnCancel.addEventListener('click', onCancel); cleanupListeners.push({el: btnCancel, type: 'click', handler: onCancel}); }
            dialog.addEventListener('cancel', onCancel); cleanupListeners.push({el: dialog, type: 'cancel', handler: onCancel});
            dialog.addEventListener('click', onBackdropClick); cleanupListeners.push({el: dialog, type: 'click', handler: onBackdropClick});
            document.addEventListener('keydown', onKey); cleanupListeners.push({el: document, type: 'keydown', handler: onKey});

            // show the dialog
            try {
                if (typeof dialog.showModal === 'function') {
                    dialog.showModal();
                } else {
                    // fallback for old browsers
                    dialog.style.display = 'block';
                }
            } catch (e) {
                // If dialog is already open, close then open to reset state
                try { dialog.close(); } catch (ex) { }
                try { dialog.showModal(); } catch (ex) { dialog.style.display = 'block'; }
            }

            // focus confirm button for quick action
            if (btnConfirm) btnConfirm.focus();
        });
    }

    // expose
    window.showConfirm = showConfirm;
    window.confirmDialog = showConfirm; // alias
})();


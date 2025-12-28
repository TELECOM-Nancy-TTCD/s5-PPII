// Minimal notification system used by the site.
// Usage: window.notify('success', 'Operation completed', 5000)
(function () {
    'use strict';

    const containerSelector = '.notification-container';
    const templateItemSelector = '.notification-item.template';

    function findContainer() {
        return document.querySelector(containerSelector);
    }

    function attachHandlersTo(item) {
        const closeBtn = item.querySelector('.notification-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                removeNotification(item);
            });
        }
    }

    function removeNotification(item) {
        if (!item) return;
        // clear any pending timeout
        if (item._notifTimeout) clearTimeout(item._notifTimeout);
        item.classList.add('hiding');
        // small delay so CSS transition (if present) can play
        setTimeout(() => {
            item.remove();
        }, 300);
    }

    function createNotification(type = 'info', text = '', duration = 5000) {
        const container = findContainer();
        if (!container) {
            console.warn('Notification container not found');
            return null;
        }

        // clone template item if exists (hidden), otherwise build one
        let template = container.querySelector(templateItemSelector);
        let node;
        if (template) {
            node = template.cloneNode(true);
            // make it visible: remove template marker and inline display:none
            node.classList.remove('template');
            node.removeAttribute('style');
            node.removeAttribute('aria-hidden');
        } else {
            node = document.createElement('li');
            node.className = 'notification-item';
            node.innerHTML = '<div class="notification-content"><div class="notification-icon"></div><div class="notification-text"></div></div><div class="notification-icon notification-close">&times;</div><div class="notification-progress-bar"></div>';
        }

        node.classList.remove('success', 'info', 'warning', 'error');
        if (type) node.classList.add(type);
        switch (type) {
            case 'success':
                node.querySelector('.notification-icon').innerHTML = '<i class="fa-regular fa-circle-check"></i>';
                break;
            case 'info':
                node.querySelector('.notification-icon').innerHTML = '<i class="fa-regular fa-circle-info"></i>';
                break;
            case 'warning':
                node.querySelector('.notification-icon').innerHTML = '<i class="fa-regular fa-triangle-exclamation"></i>';
                break;
            case 'error':
                node.querySelector('.notification-icon').innerHTML = '<i class="fa-regular fa-circle-xmark"></i>';
                break;
            default:
                node.querySelector('.notification-icon').innerHTML = '<i class="fa-solid fa-bell"></i>';
        }

        const textNode = node.querySelector('.notification-text');
        if (textNode) textNode.textContent = text;

        // set CSS variable for duration so CSS animation uses it
        // Expectation: CSS reads --notif-duration in ms (e.g. "5000ms").
        const msValue = Math.max(0, Number(duration)) + 'ms';
        node.style.setProperty('--notif-duration', msValue);

        // reset progress bar: remove inline width/transition if present so CSS animation applies
        const bar = node.querySelector('.notification-progress-bar');
        if (bar) {
            bar.style.transition = '';
            bar.style.width = '';
            // force reflow to ensure the CSS animation restarts
            void bar.offsetWidth;
            // remove any inline animation to let CSS variable-driven animation run from start
            bar.style.animation = '';
            // force reflow again
            void bar.offsetWidth;
            // To ensure the animation restarts in some browsers, toggle a class (not necessary here)
        }

        attachHandlersTo(node);

        // insert at top so newest notifications are visible first
        container.insertBefore(node, container.firstChild);

        if (duration > 0) {
            node._notifTimeout = setTimeout(() => {
                removeNotification(node);
            }, duration);
        }

        return node;
    }

    // small helper to persist notifications across a redirect using sessionStorage
    function persistNotification(type = 'info', text = '', duration = 5000) {
        try {
            const key = 'tns_pending_notifs';
            const raw = sessionStorage.getItem(key);
            let arr = [];
            if (raw) {
                try { arr = JSON.parse(raw) || []; } catch (e) { arr = []; }
            }
            arr.push({ type: type, text: text, duration: duration });
            sessionStorage.setItem(key, JSON.stringify(arr));
        } catch (e) {
            console.warn('Could not persist notification', e);
        }
    }

    // helper to persist then redirect
    function notifyAndRedirect(type, text, duration, url) {
        persistNotification(type, text, duration);
        if (typeof url === 'string' && url.length > 0) {
            window.location.href = url;
        }
        return true;
    }

    // attach handlers to existing items (close buttons) and ensure their animation duration follows --notif-duration
    document.addEventListener('DOMContentLoaded', function () {
        const container = findContainer();
        if (!container) return;
        container.querySelectorAll('.notification-item').forEach(item => {
            // skip template marker
            if (item.classList.contains('template')) return;
            attachHandlersTo(item);
            // if the element has a --notif-duration inline or attribute, let CSS handle the animation
            // If not, set a default of 5000ms and schedule removal
            const computed = getComputedStyle(item).getPropertyValue('--notif-duration').trim();
            let durationMs = 5000;
            if (computed) {
                const parsed = parseInt(computed.replace(/[^0-9]/g, ''), 10);
                if (!Number.isNaN(parsed) && parsed > 0) durationMs = parsed;
            }

            const bar = item.querySelector('.notification-progress-bar');
            if (bar) {
                // ensure the CSS animation is reset so it starts from the beginning
                bar.style.animation = '';
                void bar.offsetWidth;
                bar.style.animation = `progressBar ${durationMs}ms linear forwards`;
            }

            // auto remove after durationMs
            item._notifTimeout = setTimeout(() => {
                removeNotification(item);
            }, durationMs);
        });

        // read any pending notifications stored in sessionStorage (from a previous page before redirect)
        try {
            const key = 'tns_pending_notifs';
            const raw = sessionStorage.getItem(key);
            if (raw) {
                let arr = [];
                try { arr = JSON.parse(raw) || []; } catch (e) { arr = []; }
                if (Array.isArray(arr) && arr.length) {
                    arr.forEach(n => {
                        try {
                            createNotification(n.type || 'info', n.text || '', n.duration || 5000);
                        } catch (e) { /* ignore */ }
                    });
                }
                // remove after consumption
                sessionStorage.removeItem(key);
            }
        } catch (e) {
            // ignore sessionStorage errors
            console.warn('Could not read persisted notifications', e);
        }
    }, false);

    // Ajout dans l'API de la création de notification
    window.notify = createNotification;
    window.persistNotification = persistNotification;
    window.notifyAndRedirect = notifyAndRedirect;

})();

// Script pour recherche de clients avec suggestions en temps réel
// Comportement :
// - Récupère /api/clients une fois et met en cache
// - Filtre localement les clients quand l'utilisateur tape
// - Affiche des suggestions cliquables et navigables au clavier
// - Remplit #client-search (texte affiché) et #client-id (hidden) avec l'ID

(function(){
    const searchInput = document.getElementById('client-search');
    const hiddenId = document.getElementById('client-id');
    const suggestions = document.getElementById('client-suggestions');
    const BOX_ACTIVE_CLASS = 'active';

    if (!searchInput || !hiddenId || !suggestions) return;

    let clientsCache = [];
    let filtered = [];
    let selectedIndex = -1;

    // Fetch clients once and cache
    async function loadClients(){
        try{
            const resp = await fetch('/api/clients', {credentials: 'same-origin'});
            if (!resp.ok) throw new Error('Erreur fetch clients');
            const data = await resp.json();
            clientsCache = Array.isArray(data.clients) ? data.clients : [];
        }catch(e){
            console.warn('Impossible de charger la liste des clients:', e);
            clientsCache = [];
        }
    }

    // Normalise une chaîne pour comparaison
    function normalize(s){
        return String(s || '').toLowerCase();
    }

    // Filtrer localement
    function filterClients(q){
        if (!q) return [];
        const nq = normalize(q);
        return clientsCache.filter(c => {
            // Rechercher dans nom, prenom, email, telephone, raison_sociale si présents
            const fields = [c.nom_entreprise, c.contact_nom, c.contact_email, c.contact_telephone];
            return fields.some(f => normalize(f).includes(nq));
        }).slice(0, 10); // limiter le nombre de suggestions
    }

    // Construire la liste de suggestions
    function renderSuggestions(list){
        suggestions.innerHTML = '';
        if (!list || list.length === 0){
            suggestions.classList.add('hidden');
            selectedIndex = -1;
            return;
        }
        suggestions.classList.remove('hidden');
        list.forEach((c, idx) => {
            const li = document.createElement('li');
            li.className = 'client-suggestion';
            li.setAttribute('role', 'option');
            li.setAttribute('data-id', c.client_id ?? c.id ?? '');
            li.setAttribute('data-idx', idx);
            li.tabIndex = -1;
            // Texte affiché : prénom nom (email)
            const display = [c.nom_entreprise].filter(Boolean).join(' ') || c.contact_email || 'Client';
            li.textContent = display + (c.email ? ` — ${c.email}` : '');
            li.addEventListener('click', () => selectClient(idx));
            suggestions.appendChild(li);
        });
        selectedIndex = -1;
    }

    // Sélectionner un client par index dans filtered
    function selectClient(index){
        const c = filtered[index];
        if (!c) return;
        const id = c.client_id ?? c.id ?? '';
        const display = [c.nom_entreprise].filter(Boolean).join(' ') || c.contact_email || '';
        searchInput.value = display;
        hiddenId.value = id;
        // masquer suggestions
        suggestions.classList.add('hidden');
        // déclencher un event change sur le hidden (utile pour les formulaires dynamiques)
        hiddenId.dispatchEvent(new Event('change', {bubbles: true}));
    }

    function highlight(index){
        const items = suggestions.querySelectorAll('.client-suggestion');
        items.forEach(it => it.classList.remove('highlight'));
        if (index < 0 || index >= items.length) return;
        items[index].classList.add('highlight');
        // scroll into view
        items[index].scrollIntoView({block: 'nearest'});
    }

    // Événements
    searchInput.addEventListener('input', (e) => {
        const q = e.target.value.trim();
        if (!q){
            filtered = [];
            hiddenId.value = '';
            renderSuggestions([]);
            return;
        }
        filtered = filterClients(q);
        renderSuggestions(filtered);
    });

    searchInput.addEventListener('keydown', (e) => {
        const items = suggestions.querySelectorAll('.client-suggestion');
        if (e.key === 'ArrowDown'){
            e.preventDefault();
            if (selectedIndex < items.length - 1) selectedIndex++;
            highlight(selectedIndex);
        }else if (e.key === 'ArrowUp'){
            e.preventDefault();
            if (selectedIndex > 0) selectedIndex--;
            highlight(selectedIndex);
        }else if (e.key === 'Enter'){
            if (selectedIndex >= 0 && selectedIndex < items.length){
                e.preventDefault();
                selectClient(selectedIndex);
            }
        }else if (e.key === 'Escape'){
            suggestions.classList.add('hidden');
            selectedIndex = -1;
        }
    });

    // Clic en-dehors pour fermer
    document.addEventListener('click', (e) => {
        if (!document.getElementById('client-search-box').contains(e.target)){
            suggestions.classList.add('hidden');
        }
    });

    // Au focus, si le champ comporte du texte, afficher les suggestions adaptées
    searchInput.addEventListener('focus', (e) => {
        const q = e.target.value.trim();
        if (q){
            filtered = filterClients(q);
            renderSuggestions(filtered);
        }
    });

    // Initialisation
    loadClients().then(r => {});

    // Si le champ de recherche contient un id pré-sélectionné (data-selected-id), remplir le hidden
    (function initPreselected(){
        try{
            const preId = searchInput.getAttribute('data-selected-id');
            if (preId && preId.trim()){
                hiddenId.value = preId;
            }
        }catch(e){/* ignore */}
    })();

 })();


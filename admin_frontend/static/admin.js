// This is the complete, corrected file.
document.addEventListener('DOMContentLoaded', () => {
    // --- UI Elements ---
    const navLinks = document.querySelectorAll('.nav-link');
    const views = document.querySelectorAll('.view');
    const createCollectionModal = document.getElementById('create-collection-modal');
    const createAdminModal = document.getElementById('create-admin-modal');
    const collectionNameInput = document.getElementById('update-collection-name');
    const collectionSourceDropdown = document.getElementById('collection-source-dropdown');
    const geocodedAddressEl = document.getElementById('reverse-geocoded-address');

    // --- State & Map Variables ---
    let map = null;
    let marker = null;
    let currentLatitude = 27.1751;
    let currentLongitude = 78.0421;
    let fetchedViews = new Set();

    // --- Helper & Utility Functions ---
    const showLoader = (tbody) => {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center text-slate-500 py-12"><i class="fa-solid fa-spinner fa-spin text-2xl"></i><p class="mt-2">Loading data...</p></td></tr>';
    };
    const showEmpty = (tbody, message) => {
        tbody.innerHTML = `<tr><td colspan="10" class="text-center text-slate-500 py-12">${message}</td></tr>`;
    };
    
    // --- Map & Geocoding Functions ---
    async function updateReverseGeocodedAddress(lat, lon) {
        geocodedAddressEl.textContent = 'Fetching address...';
        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}`);
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            geocodedAddressEl.textContent = data.display_name || 'No address found.';
        } catch (error) {
            console.error('Reverse geocoding failed:', error);
            geocodedAddressEl.textContent = 'Could not fetch address.';
        }
    }
    
    function initializeMap() {
        if (map) {
            map.invalidateSize();
            map.setView([currentLatitude, currentLongitude], 16);
            marker.setLatLng([currentLatitude, currentLongitude]);
        } else {
            map = L.map('map').setView([currentLatitude, currentLongitude], 16);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap'
            }).addTo(map);
            marker = L.marker([currentLatitude, currentLongitude], { draggable: true }).addTo(map);
            marker.on('dragend', function (e) {
                const latlng = e.target.getLatLng();
                currentLatitude = latlng.lat;
                currentLongitude = latlng.lng;
                updateReverseGeocodedAddress(currentLatitude, currentLongitude);
            });
        }
        updateReverseGeocodedAddress(currentLatitude, currentLongitude);
    }

    // --- Data Fetching Functions ---
    async function fetchCollectionsData() {
        const tbody = document.getElementById('collections-table-body');
        showLoader(tbody);
        try {
            const response = await fetch('/api/admin/collections');
            if (!response.ok) throw new Error('Failed to fetch collections');
            const data = await response.json();
            renderCollections(data.collections);
            fetchedViews.add('view-collections');
        } catch (error) { showEmpty(tbody, `Error: ${error.message}`); }
    }
    async function fetchGuestsData() {
        const tbody = document.getElementById('guests-table-body');
        showLoader(tbody);
        try {
            const response = await fetch('/api/admin/guests');
            if (!response.ok) throw new Error('Failed to fetch guests');
            const data = await response.json();
            renderGuests(data.guests);
            fetchedViews.add('view-guests');
        } catch (error) { showEmpty(tbody, `Error: ${error.message}`); }
    }
    async function fetchActivitiesData() {
        const tbody = document.getElementById('activities-table-body');
        showLoader(tbody);
        try {
            const response = await fetch('/api/admin/activities');
            if (!response.ok) throw new Error('Failed to fetch activities');
            const data = await response.json();
            renderActivities(data.activities);
            fetchedViews.add('view-activities');
        } catch (error) { showEmpty(tbody, `Error: ${error.message}`); }
    }
    async function fetchAdminsData() {
        const tbody = document.getElementById('admins-table-body');
        showLoader(tbody);
        try {
            const response = await fetch('/api/admin/admins');
            if (!response.ok) throw new Error('Failed to fetch admins');
            const data = await response.json();
            renderAdmins(data.admins);
            fetchedViews.add('view-admins');
        } catch (error) { showEmpty(tbody, `Error: ${error.message}`); }
    }

    // --- Data Rendering Functions ---
    function renderCollections(collections) {
        const tbody = document.getElementById('collections-table-body');
        if (!collections || collections.length === 0) {
            return showEmpty(tbody, 'No collections found. Click "New Collection" to begin.');
        }
        tbody.innerHTML = collections.map(col => {
            const imageCount = col.total_images;
            const countClass = (typeof imageCount === 'number' && imageCount > 0) ? 'text-green-600' : 'text-slate-500';
            return `<tr>
                <td><input type="checkbox" class="check-item" data-table="collections" data-name="${col.name}"></td>
                <!-- FIX: Changed text-white to text-gray-900 for readability on light theme -->
                <td class="font-semibold text-gray-900">${col.name}</td>
                <!-- FIX: Added location-cell class for better wrapping, changed color class -->
                <td class="location-cell text-gray-600">${col.location || 'N/A'}</td>
                <td class="text-gray-600">${col.upload_datetime}</td>
                <td class="font-bold ${countClass}">${imageCount}</td>
                <td class="space-x-2 text-center">
                    <button class="action-btn sync" data-name="${col.name}" data-source-folder="${col.source_folder}" title="Sync Collection"><i class="fa-solid fa-arrows-rotate"></i></button>
                </td>
            </tr>`;
        }).join('');
    }
    function renderGuests(guests) {
        const tbody = document.getElementById('guests-table-body');
        if (!guests || guests.length === 0) return showEmpty(tbody, 'No guests have logged in yet.');
        // FIX: Changed text-white to text-gray-900
        tbody.innerHTML = guests.map(g => `<tr><td><input type="checkbox" class="check-item" data-table="guests" data-id="${g.id}"></td><td class="font-mono">${g.id}</td><td class="font-semibold text-gray-900">${g.name}</td><td>${g.mobile_number}</td><td>${g.created_at}</td></tr>`).join('');
    }
    function renderActivities(activities) {
        const tbody = document.getElementById('activities-table-body');
        if (!activities || activities.length === 0) return showEmpty(tbody, 'No guest activity recorded yet.');
        // FIX: Changed text-white and text-slate-400 to more readable colors
        tbody.innerHTML = activities.map(act => `<tr><td><input type="checkbox" class="check-item" data-table="activities" data-id="${act.id}"></td><td>${act.timestamp}</td><td class="font-semibold text-gray-900">${act.guest_name}</td><td>${act.action}</td><td class="text-gray-500 font-mono text-sm">${act.details || ''}</td></tr>`).join('');
    }
    function renderAdmins(admins) {
        const tbody = document.getElementById('admins-table-body');
        if (!admins || admins.length === 0) return showEmpty(tbody, 'No admin users found.');
        tbody.innerHTML = admins.map(admin => {
            const checkbox = admin.id === 1 ? '' : `<input type="checkbox" class="check-item" data-table="admins" data-id="${admin.id}">`;
            const deleteBtn = admin.id === 1 ? '' : `<button class="action-btn delete" data-type="admin" data-id="${admin.id}" title="Delete Admin"><i class="fa-solid fa-trash-can"></i></button>`;
            // FIX: Changed text-white to text-gray-900
            return `<tr><td>${checkbox}</td><td class="font-mono">${admin.id}</td><td class="font-semibold text-gray-900">${admin.username}</td><td class="text-center">${deleteBtn}</td></tr>`;
        }).join('');
    }
    
    // --- Navigation & Event Listeners ---
    // (This entire section remains unchanged)
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = `view-${link.id.split('-')[1]}`;
            if (!document.getElementById(targetId)) return;
            views.forEach(view => view.classList.add('hidden'));
            document.getElementById(targetId).classList.remove('hidden');
            navLinks.forEach(nav => nav.classList.remove('active'));
            link.classList.add('active');
            if (!fetchedViews.has(targetId)) {
                switch (targetId) {
                    case 'view-guests': fetchGuestsData(); break;
                    case 'view-activities': fetchActivitiesData(); break;
                    case 'view-admins': fetchAdminsData(); break;
                }
            }
        });
    });

    document.getElementById('open-create-modal-btn').addEventListener('click', async () => {
        collectionNameInput.value = '';
        collectionSourceDropdown.value = '';
        collectionSourceDropdown.innerHTML = '<option value="">-- Loading available folders... --</option>';
        createCollectionModal.classList.remove('hidden');
        setTimeout(initializeMap, 10);
        try {
            const response = await fetch('/api/admin/available-folders');
            const data = await response.json();
            collectionSourceDropdown.innerHTML = '<option value="">-- Select a Source Folder --</option>';
            if (data.folders.length === 0) {
                collectionSourceDropdown.innerHTML = '<option value="">No folders found in /images directory</option>';
            } else { data.folders.forEach(folder => { collectionSourceDropdown.innerHTML += `<option value="${folder}">${folder}</option>`; }); }
        } catch (error) { collectionSourceDropdown.innerHTML = '<option value="">Error loading folders</option>'; }
    });
    
    document.getElementById('update-modal-start-btn').addEventListener('click', async () => {
        const collectionName = collectionNameInput.value.trim().replace(/-/g, '_').replace(/\s+/g, '_').toLowerCase();
        const selectedFolder = collectionSourceDropdown.value;
        if (!collectionName || !selectedFolder) { return alert('Please provide a collection name and select a source folder.'); }
        const sourceDir = `images/${selectedFolder}`;
        const btn = document.getElementById('update-modal-start-btn');
        btn.disabled = true; btn.innerHTML = 'Processing...';
        try {
            const response = await fetch(`/api/admin/update-collection/${collectionName}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source_directory: sourceDir, latitude: currentLatitude, longitude: currentLongitude })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to update collection.');
            alert('Collection created/updated successfully!');
            createCollectionModal.classList.add('hidden');
            fetchCollectionsData();
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally { btn.disabled = false; btn.innerHTML = 'Start Indexing'; }
    });
    
    document.getElementById('admin-modal-create-btn').addEventListener('click', async () => {
        const username = document.getElementById('new-admin-username').value.trim();
        const password = document.getElementById('new-admin-password').value.trim();
        if (!username || !password) return alert('Username and password are required.');

        const btn = document.getElementById('admin-modal-create-btn');
        btn.disabled = true; btn.textContent = 'Creating...';

        try {
            const response = await fetch('/api/admin/create-admin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to create admin.');
            alert(data.message);
            createAdminModal.classList.add('hidden');
            fetchAdminsData();
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            btn.disabled = false; btn.textContent = 'Create User';
            document.getElementById('new-admin-username').value = '';
            document.getElementById('new-admin-password').value = '';
        }
    });

    // (This entire section remains unchanged)
    function handleSelectionChange(table) {
        const checkboxes = document.querySelectorAll(`.check-item[data-table="${table}"]:checked`);
        const deleteBtn = document.getElementById(`delete-selected-${table}`);
        if (deleteBtn) { deleteBtn.classList.toggle('hidden', checkboxes.length === 0); }
    }

    async function bulkDelete(type, ids = [], names = []) {
        const endpoint = `/api/admin/${type}s/bulk`;
        const body = names.length > 0 ? JSON.stringify({ names }) : JSON.stringify({ ids });
        try {
            const response = await fetch(endpoint, { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail);
            alert(data.message);
        } catch (error) { alert(`Error: ${error.message}`); }
    }

    document.querySelector('main').addEventListener('click', async (e) => {
        const syncBtn = e.target.closest('.sync');
        if (syncBtn) {
            const collectionName = syncBtn.dataset.name;
            const actualSourceFolder = syncBtn.dataset.sourceFolder;
            const sourceDir = prompt(`Confirm source directory for syncing "${collectionName}":`, actualSourceFolder);
            
            if (!sourceDir) return alert('Sync cancelled.');

            syncBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            try {
                const response = await fetch(`/api/admin/sync-collection/${collectionName}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ source_directory: sourceDir })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Sync failed.');
                alert(data.message || 'Sync complete.');
                fetchCollectionsData();
            } catch (error) {
                alert(`Error: ${error.message}`);
                syncBtn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i>';
            }
        }
    });
    
    document.body.addEventListener('change', e => {
        if (e.target.matches('.check-all')) {
            const table = e.target.dataset.table;
            document.querySelectorAll(`.check-item[data-table="${table}"]`).forEach(cb => cb.checked = e.target.checked);
            handleSelectionChange(table);
        }
        if (e.target.matches('.check-item')) { handleSelectionChange(e.target.dataset.table); }
    });
    
    document.getElementById('delete-selected-collections').addEventListener('click', async () => {
        const names = Array.from(document.querySelectorAll('.check-item[data-table="collections"]:checked')).map(cb => cb.dataset.name);
        if (names.length > 0 && confirm(`Are you sure you want to delete ${names.length} collection(s)?`)) {
            await bulkDelete('collection', [], names); fetchCollectionsData();
        }
    });
    document.getElementById('delete-selected-guests').addEventListener('click', async () => {
        const ids = Array.from(document.querySelectorAll('.check-item[data-table="guests"]:checked')).map(cb => parseInt(cb.dataset.id));
        if (ids.length > 0 && confirm(`Are you sure you want to delete ${ids.length} guest(s)?`)) {
            await bulkDelete('guest', ids); fetchGuestsData();
        }
    });
    document.getElementById('delete-selected-activities').addEventListener('click', async () => {
        const ids = Array.from(document.querySelectorAll('.check-item[data-table="activities"]:checked')).map(cb => parseInt(cb.dataset.id));
        if (ids.length > 0 && confirm(`Are you sure you want to delete ${ids.length} activit(ies)?`)) {
            await bulkDelete('activitie', ids); fetchActivitiesData();
        }
    });
    document.getElementById('delete-selected-admins').addEventListener('click', async () => {
        const ids = Array.from(document.querySelectorAll('.check-item[data-table="admins"]:checked')).map(cb => parseInt(cb.dataset.id));
        if (ids.length > 0 && confirm(`Are you sure you want to delete ${ids.length} admin(s)?`)) {
            await bulkDelete('admin', ids); fetchAdminsData();
        }
    });
    document.getElementById('get-location-btn').addEventListener('click', () => {
        geocodedAddressEl.textContent = "Getting location...";
        if (!navigator.geolocation) { return geocodedAddressEl.textContent = "Geolocation is not supported by your browser."; }
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                currentLatitude = latitude; currentLongitude = longitude;
                map.setView([latitude, longitude], 17); marker.setLatLng([latitude, longitude]);
                updateReverseGeocodedAddress(latitude, longitude);
            },
            () => geocodedAddressEl.textContent = "Unable to retrieve your location."
        );
    });
    
    document.getElementById('open-admin-modal-btn').addEventListener('click', () => createAdminModal.classList.remove('hidden'));
    document.querySelectorAll('.cancel-btn').forEach(btn => btn.addEventListener('click', () => {
        createCollectionModal.classList.add('hidden'); createAdminModal.classList.add('hidden');
    }));
    document.getElementById('logout-btn').addEventListener('click', async () => {
        const response = await fetch('/admin/logout', { method: 'POST' });
        if (response.redirected) window.location.href = response.url;
    });

    // --- Initial Load ---
    fetchCollectionsData();
});
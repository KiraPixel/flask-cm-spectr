document.addEventListener('DOMContentLoaded', () => {
    const loading = document.getElementById('loading');
    const errorDiv = document.getElementById('error');

    // Загрузка пресетов оповещений с эндпоинтом /api/alerts_presets/with_vehicle_count
    window.loadPresets = async function() {
        loading.style.display = 'block';
        try {
            const response = await fetch('/api/alerts_presets/with_vehicle_count', {
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const result = await response.json();
            loading.style.display = 'none';
            if (result.status !== 'success') {
                errorDiv.textContent = result.message || 'Ошибка при загрузке пресетов';
                errorDiv.style.display = 'block';
                return;
            }
            const container = document.getElementById('presetsContainer');
            if (!container) {
                window.showToast('Контейнер для пресетов не найден', 'danger');
                return;
            }
            container.innerHTML = '';
            // Сохраняем типы алертов для последующего использования
            window.alertTypes = [];
            const filteredPresets = result.data.filter(preset => preset.personalized !== 1);
            for (const preset of filteredPresets) {
                // Собираем все уникальные типы алертов из enable_alert_types и disable_alert_types
                const alertTypes = [...preset.enable_alert_types, ...preset.disable_alert_types];
                alertTypes.forEach(type => {
                    if (!window.alertTypes.some(t => t.alert_un === type.alert_un)) {
                        window.alertTypes.push({
                            alert_un: type.alert_un,
                            localization: type.localization
                        });
                    }
                });
                const card = document.createElement('div');
                card.className = 'col-md-6 col-lg-4';
                card.innerHTML = `
                    <div class="card border-0 shadow h-100 rounded-4">
                        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center rounded-top-4 py-3">
                            <h5 class="mb-0 fw-semibold">${preset.preset_name}</h5>
                            <div>
                                ${preset.editable ? `<button class="btn btn-sm btn-outline-light edit-preset rounded-circle ms-2" data-id="${preset.id}" data-preset_name="${preset.preset_name}" data-enable_alert_types='${JSON.stringify(preset.enable_alert_types.map(t => t.alert_un))}' data-disable_alert_types='${JSON.stringify(preset.disable_alert_types.map(t => t.alert_un))}' data-wialon_danger_distance="${preset.wialon_danger_distance}" data-wialon_danger_hours_not_work="${preset.wialon_danger_hours_not_work}" data-active="${preset.active}" data-editable="${preset.editable}" data-personalized="${preset.personalized}"><i class="bi bi-pencil"></i></button>` : ''}
                                <button class="btn btn-sm btn-outline-light delete-preset rounded-circle ms-2" data-id="${preset.id}"><i class="bi bi-trash"></i></button>
                            </div>
                        </div>
                        <div class="card-body py-3 d-flex flex-wrap gap-2">
                            <div class="d-flex align-items-center me-3 mb-2">
                                <i class="bi bi-truck me-2 text-primary"></i>
                                <span class="badge bg-primary-subtle text-primary rounded-pill">${preset.vehicle_count}</span>
                            </div>
                            <div class="d-flex align-items-center me-3 mb-2">
                                <i class="bi bi-power me-2 text-primary"></i>
                                <span class="badge ${preset.active ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'} rounded-pill">${preset.active ? 'Да' : 'Нет'}</span>
                            </div>
                            <div class="d-flex align-items-center me-3 mb-2">
                                <i class="bi bi-bell-fill me-2 text-primary"></i>
                                <span class="badge bg-primary-subtle text-primary rounded-pill">${preset.enable_alert_types.length}</span>
                            </div>
                            <div class="d-flex align-items-center me-3 mb-2">
                                <i class="bi bi-bell-slash-fill me-2 text-primary"></i>
                                <span class="badge bg-primary-subtle text-primary rounded-pill">${preset.disable_alert_types.length}</span>
                            </div>
                            <div class="d-flex align-items-center me-3 mb-2">
                                <i class="bi bi-rulers me-2 text-primary"></i>
                                <span class="badge bg-primary-subtle text-primary rounded-pill">${preset.wialon_danger_distance} км</span>
                            </div>
                            <div class="d-flex align-items-center me-3 mb-2">
                                <i class="bi bi-clock-fill me-2 text-primary"></i>
                                <span class="badge bg-primary-subtle text-primary rounded-pill">${preset.wialon_danger_hours_not_work} ч</span>
                            </div>
                            <div class="d-flex align-items-center mb-2">
                                ${preset.editable ? '<i class="bi bi-pencil-fill me-2 text-primary"></i>' : ''}
                                <span class="badge bg-primary-subtle text-primary rounded-pill">${preset.editable ? 'Да' : 'Нет'}</span>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            }
            document.querySelectorAll('.edit-preset').forEach(button => {
                button.addEventListener('click', () => {
                    const presetId = button.getAttribute('data-id');
                    const presetName = button.getAttribute('data-preset_name');
                    const enableAlertTypes = JSON.parse(button.getAttribute('data-enable_alert_types'));
                    const disableAlertTypes = JSON.parse(button.getAttribute('data-disable_alert_types'));
                    const wialonDangerDistance = button.getAttribute('data-wialon_danger_distance');
                    const wialonDangerHoursNotWork = button.getAttribute('data-wialon_danger_hours_not_work');
                    const active = button.getAttribute('data-active');
                    const editable = button.getAttribute('data-editable');
                    const personalized = button.getAttribute('data-personalized');
                    document.getElementById('presetModalLabel').textContent = 'Редактировать пресет';
                    document.getElementById('presetId').value = presetId;
                    document.getElementById('presetName').value = presetName;
                    document.getElementById('wialonDangerDistance').value = wialonDangerDistance;
                    document.getElementById('wialonDangerHoursNotWork').value = wialonDangerHoursNotWork;
                    document.getElementById('active').value = active;
                    document.getElementById('editable').value = editable;
                    document.getElementById('personalized').value = personalized;
                    window.populateAlertTypeControls({ enable_alert_types: enableAlertTypes, disable_alert_types: disableAlertTypes });
                    bootstrap.Modal.getOrCreateInstance(document.getElementById('presetModal')).show();
                });
            });
            document.querySelectorAll('.delete-preset').forEach(button => {
                button.addEventListener('click', () => window.deletePreset(button.getAttribute('data-id')));
            });
        } catch (error) {
            loading.style.display = 'none';
            errorDiv.textContent = 'Ошибка при загрузке пресетов: ' + error.message;
            errorDiv.style.display = 'block';
        }
    };

    // Заполнение списка типов алертов
    window.populateAlertTypeControls = function(preset = null) {
        const container = document.getElementById('alertTypesContainer');
        container.innerHTML = '';
        if (!window.alertTypes || window.alertTypes.length === 0) {
            window.showToast('Типы алертов не загружены', 'danger');
            return;
        }
        window.alertTypes.forEach(type => {
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center rounded-3 mb-2 p-3 border';
            item.innerHTML = `
                <span class="me-3">${type.localization}</span>
                <div class="btn-group" role="group" data-alert-un="${type.alert_un}">
                    <button type="button" class="btn btn-sm btn-outline-success alert-state me-1" data-state="enabled"><i class="bi bi-check-circle"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-danger alert-state me-1" data-state="disabled"><i class="bi bi-x-circle"></i></button>
                    <button type="button" class="btn btn-sm btn-outline-secondary alert-state${preset && !preset.enable_alert_types.includes(type.alert_un) && !preset.disable_alert_types.includes(type.alert_un) ? ' active' : ''}" data-state="inherited"><i class="bi bi-dash-circle"></i></button>
                </div>
            `;
            if (preset) {
                if (preset.enable_alert_types.includes(type.alert_un)) {
                    item.querySelector('[data-state="enabled"]').classList.add('active');
                } else if (preset.disable_alert_types.includes(type.alert_un)) {
                    item.querySelector('[data-state="disabled"]').classList.add('active');
                }
            } else {
                item.querySelector('[data-state="inherited"]').classList.add('active');
            }
            container.appendChild(item);
        });
        document.querySelectorAll('.alert-state').forEach(button => {
            button.addEventListener('click', () => {
                const group = button.closest('.btn-group');
                group.querySelectorAll('.alert-state').forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
            });
        });
    };

    // Функция для создания/редактирования пресета
    document.getElementById('presetForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const presetId = document.getElementById('presetId').value;
        const enableAlertTypes = [];
        const disableAlertTypes = [];
        document.querySelectorAll('#alertTypesContainer .btn-group').forEach(group => {
            const alertUn = group.getAttribute('data-alert-un');
            const activeState = group.querySelector('.alert-state.active').getAttribute('data-state');
            if (activeState === 'enabled') {
                enableAlertTypes.push(alertUn);
            } else if (activeState === 'disabled') {
                disableAlertTypes.push(alertUn);
            }
        });
        const presetData = {
            preset_name: document.getElementById('presetName').value,
            enable_alert_types: enableAlertTypes,
            disable_alert_types: disableAlertTypes,
            wialon_danger_distance: parseInt(document.getElementById('wialonDangerDistance').value),
            wialon_danger_hours_not_work: parseInt(document.getElementById('wialonDangerHoursNotWork').value),
            active: parseInt(document.getElementById('active').value),
            editable: parseInt(document.getElementById('editable').value),
            personalized: parseInt(document.getElementById('personalized').value)
        };
        const method = presetId ? 'PUT' : 'POST';
        const url = presetId ? `/api/alerts_presets/${presetId}` : '/api/alerts_presets';
        loading.style.display = 'block';
        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(presetData)
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            loading.style.display = 'none';
            if (data.status === 'success') {
                window.showToast(presetId ? 'Пресет успешно обновлен' : 'Пресет успешно создан');
                bootstrap.Modal.getInstance(document.getElementById('presetModal')).hide();
                window.loadPresets();
            } else {
                window.showToast(data.message || 'Ошибка при сохранении пресета', 'danger');
            }
        } catch (error) {
            loading.style.display = 'none';
            window.showToast('Ошибка при сохранении пресета: ' + error.message, 'danger');
        }
    });

    // Функция для удаления пресета
    window.deletePreset = async function(presetId) {
        if (confirm('Вы уверены, что хотите удалить пресет?')) {
            loading.style.display = 'block';
            try {
                const response = await fetch(`/api/alerts_presets/${presetId}`, {
                    method: 'DELETE'
                });
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                loading.style.display = 'none';
                if (data.status === 'success') {
                    window.showToast('Пресет успешно удален');
                    window.loadPresets();
                } else {
                    window.showToast(data.message || 'Ошибка при удалении пресета', 'danger');
                }
            } catch (error) {
                loading.style.display = 'none';
                window.showToast('Ошибка при удалении пресета: ' + error.message, 'danger');
            }
        }
    };

    // Обработчик для создания нового пресета
    document.querySelector('[data-bs-target="#presetModal"]').addEventListener('click', () => {
        document.getElementById('presetModalLabel').textContent = 'Новый пресет';
        document.getElementById('presetForm').reset();
        document.getElementById('presetId').value = '';
        document.getElementById('wialonDangerDistance').value = '5';
        document.getElementById('wialonDangerHoursNotWork').value = '72';
        document.getElementById('active').value = '1';
        document.getElementById('editable').value = '1';
        document.getElementById('personalized').value = '0';
        window.populateAlertTypeControls();
    });
});
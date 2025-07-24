document.addEventListener('DOMContentLoaded', () => {
    const loading = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const container = document.getElementById('storagesContainer');

    // Функция для показа уведомлений через Bootstrap alert
    const showAlert = (message, type) => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed bottom-0 start-50 translate-middle-x mb-4 shadow`;
        alertDiv.style.zIndex = '1050';
        alertDiv.style.width = '90%';
        alertDiv.style.maxWidth = '500px';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Закрыть"></button>
        `;
        document.body.appendChild(alertDiv);
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    };

    // Загрузка складов
    window.loadStorages = async function() {
        if (!container || !loading || !errorDiv) {
            console.error('Необходимые элементы DOM не найдены');
            showAlert('Ошибка инициализации интерфейса', 'danger');
            return;
        }

        loading.style.display = 'block';
        errorDiv.style.display = 'none';
        container.innerHTML = '';

        try {
            const response = await fetch('/api/admin/storage', {
                headers: { 'Content-Type': 'application/json' },
                redirect: 'follow',
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            if (!Array.isArray(data)) throw new Error('Неверный формат данных');

            data.forEach(storage => {
                const card = document.createElement('div');
                card.className = 'col-md-6 col-lg-4';
                card.innerHTML = `
                    <div class="card border-0 shadow-sm h-100 rounded-4 overflow-hidden transition-all">
                        <div class="card-header bg-body-secondary d-flex justify-content-between align-items-center rounded-top-4 py-3 px-4">
                            <h5 class="mb-0 fw-semibold">${storage.named}</h5>
                            <div class="d-flex gap-2">
                                <button class="btn btn-sm edit-storage rounded-circle transition-all" data-id="${storage.id}" data-name="${storage.named}" data-x="${storage.pos_x}" data-y="${storage.pos_y}" data-radius="${storage.radius}" data-bs-toggle="modal" data-bs-target="#storageModal">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-sm btn-danger delete-storage rounded-circle transition-all" data-id="${storage.id}">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="card-body py-4 px-4 d-flex flex-column gap-2">
                            <div class="d-flex align-items-center gap-3">
                                <div class="d-flex align-items-center">
                                    <i class="bi bi-geo-alt-fill me-2 text-primary"></i>
                                    <a href="https://yandex.ru/maps/?pt=${storage.pos_y},${storage.pos_x}&z=15&l=map" target="_blank" class="badge badge-custom rounded-pill coords-link">${storage.pos_x}, ${storage.pos_y}</a>
                                </div>
                                <div class="d-flex align-items-center">
                                    <i class="bi bi-circle me-2 text-primary"></i>
                                    <span class="badge badge-custom rounded-pill">${storage.radius} км</span>
                                </div>
                            </div>
                            <div class="d-flex align-items-center">
                                <i class="bi bi-house me-2 text-primary"></i>
                                <a href="#" class="badge badge-custom rounded-pill address-link" data-bs-toggle="tooltip" data-bs-title="${storage.address}" data-address="${storage.address}">${storage.address}</a>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });

            // Инициализация tooltip'ов для адреса
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltipTriggerList.forEach(tooltipTriggerEl => {
                new bootstrap.Tooltip(tooltipTriggerEl, {
                    trigger: 'hover',
                    placement: 'top'
                });
            });

            // Обработчики для кнопок редактирования
            document.querySelectorAll('.edit-storage').forEach(button => {
                button.addEventListener('click', () => {
                    const modalLabel = document.getElementById('storageModalLabel');
                    const storageId = button.getAttribute('data-id');
                    const storageName = button.getAttribute('data-name');
                    const storageX = button.getAttribute('data-x');
                    const storageY = button.getAttribute('data-y');
                    const storageRadius = button.getAttribute('data-radius');

                    modalLabel.textContent = 'Редактировать склад';
                    document.getElementById('storageId').value = storageId;
                    document.getElementById('storageName').value = storageName;
                    document.getElementById('storageX').value = storageX;
                    document.getElementById('storageY').value = storageY;
                    document.getElementById('storageRadius').value = storageRadius;
                    document.getElementById('storageSubmitBtn').innerHTML = '<i class="bi bi-save me-2"></i>Сохранить изменения';
                });
            });

            // Обработчики для кнопок удаления
            document.querySelectorAll('.delete-storage').forEach(button => {
                button.addEventListener('click', () => window.deleteStorage(button.getAttribute('data-id')));
            });

            // Обработчики для копирования адреса
            document.querySelectorAll('.address-link').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const address = link.getAttribute('data-address');
                    navigator.clipboard.writeText(address).then(() => {
                        showAlert('Адрес скопирован в буфер обмена', 'success');
                    }).catch(() => {
                        showAlert('Ошибка при копировании адреса', 'danger');
                    });
                });
            });

        } catch (error) {
            console.error('Ошибка при загрузке складов:', error);
            showAlert(`Ошибка при загрузке складов: ${error.message}`, 'danger');
        } finally {
            loading.style.display = 'none';
        }
    };

    // Сброс формы при открытии модального окна для добавления
    document.getElementById('storageModal').addEventListener('show.bs.modal', (e) => {
        if (!e.relatedTarget.classList.contains('edit-storage')) {
            document.getElementById('storageForm').reset();
            document.getElementById('storageId').value = '';
            document.getElementById('storageModalLabel').textContent = 'Добавить склад';
            document.getElementById('storageSubmitBtn').innerHTML = '<i class="bi bi-save me-2"></i>Сохранить';
        }
    });

    // Обработка формы добавления/редактирования склада
    document.getElementById('storageForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(document.getElementById('storageForm'));
        const storageId = document.getElementById('storageId').value;
        const url = storageId ? `/api/admin/storage/edit/${storageId}` : '/api/admin/storage/add';
        const method = storageId ? 'PUT' : 'POST';

        loading.style.display = 'block';
        try {
            const response = await fetch(url, {
                method: method,
                body: formData,
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            if (data.status === 'storage_added' || data.status === 'storage_updated') {
                showAlert(data.status === 'storage_added' ? 'Склад успешно добавлен' : 'Склад успешно обновлен', 'success');
                bootstrap.Modal.getInstance(document.getElementById('storageModal')).hide();
                window.loadStorages();
            } else {
                showAlert(data.message || 'Ошибка при сохранении склада', 'danger');
            }
        } catch (error) {
            console.error('Ошибка при сохранении склада:', error);
            showAlert(`Ошибка при сохранении склада: ${error.message}`, 'danger');
        } finally {
            loading.style.display = 'none';
        }
    });

    // Функция для удаления склада
    window.deleteStorage = async function(storageId) {
        if (confirm('Вы уверены, что хотите удалить склад?')) {
            loading.style.display = 'block';
            try {
                const response = await fetch(`/api/admin/storage/delete/${storageId}`, {
                    method: 'DELETE',
                    credentials: 'same-origin'
                });
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                if (data.status === 'storage_deleted') {
                    showAlert('Склад успешно удален', 'success');
                    window.loadStorages();
                } else {
                    showAlert(data.message || 'Ошибка при удалении склада', 'danger');
                }
            } catch (error) {
                console.error('Ошибка при удалении склада:', error);
                showAlert(`Ошибка при удалении склада: ${error.message}`, 'danger');
            } finally {
                loading.style.display = 'none';
            }
        }
    };
});
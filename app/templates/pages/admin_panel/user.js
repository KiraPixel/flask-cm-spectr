document.addEventListener('DOMContentLoaded', () => {
    // Функция для показа уведомлений
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
        setTimeout(() => alertDiv.remove(), 3000);
    };

    // Загрузка списка пользователей
    window.loadUsers = async function() {
        try {
            const response = await fetch('/api/admin/users/', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка загрузки пользователей');
            const users = await response.json();
            const tbody = document.getElementById('usersTableBody');
            tbody.innerHTML = '';
            users.forEach(user => {
                tbody.innerHTML += `
                    <tr>
                        <td class="ps-4">${user.role === 1 ? '<i class="bi bi-star-fill me-2 text-warning"></i>' : ''}${user.username}</td>
                        <td>${user.email}</td>
                        <td>${user.last_activity}</td>
                        <td class="pe-4">
                            <div class="d-flex gap-2">
                                <button class="btn btn-sm btn-outline-primary rounded-circle" data-bs-toggle="modal" data-bs-target="#editUserModal" data-user-id="${user.id}" title="Редактировать" onclick="populateEditForm(${user.id}, '${user.username}', '${user.email}', ${user.role})">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger rounded-circle" data-bs-toggle="modal" data-bs-target="#resetPasswordModal" data-user-id="${user.id}" title="Сбросить пароль">
                                    <i class="bi bi-key"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-secondary rounded-circle" data-bs-toggle="modal" data-bs-target="#userTransportAccessModal" data-user-id="${user.id}" title="Настройка доступа к транспорту">
                                    <i class="bi bi-bus-front"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-info rounded-circle" data-bs-toggle="modal" data-bs-target="#userFunctionalityRolesModal" data-user-id="${user.id}" title="Настройка ролей функциональности">
                                    <i class="bi bi-gear"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
        } catch (error) {
            console.error('Ошибка при загрузке пользователей:', error);
            showAlert('Ошибка загрузки пользователей', 'danger');
        }
    };

    // Поиск пользователей
    document.getElementById('userSearch').addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const rows = document.querySelectorAll('#usersTableBody tr');
        rows.forEach(row => {
            const username = row.cells[0].textContent.toLowerCase();
            const email = row.cells[1].textContent.toLowerCase();
            row.style.display = (username.includes(searchTerm) || email.includes(searchTerm)) ? '' : 'none';
        });
    });

    // Заполнение формы редактирования
    window.populateEditForm = (id, username, email, role) => {
        document.getElementById('editUserForm').dataset.userId = id;
        document.getElementById('editUsername').value = username;
        document.getElementById('editEmail').value = email;
        document.getElementById('editRole').value = role;
    };

    // Обработка отправки формы приглашения
    document.getElementById('inviteUserForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        try {
            const response = await fetch('/api/admin/users/add', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка приглашения пользователя');
            const result = await response.json();
            if (result.status === 'user_added') {
                bootstrap.Modal.getInstance(document.getElementById('inviteUserModal')).hide();
                showAlert('Пользователь успешно приглашен', 'success');
                window.loadUsers();
            } else {
                showAlert('Ошибка при приглашении пользователя', 'danger');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showAlert('Произошла ошибка', 'danger');
        }
    });

    // Обработка отправки формы редактирования
    document.getElementById('editUserForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const userId = e.target.dataset.userId;
        const formData = new FormData(e.target);
        try {
            const response = await fetch(`/api/admin/users/edit/${userId}`, {
                method: 'PUT',
                body: formData,
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка редактирования пользователя');
            const result = await response.json();
            if (result.status === 'user_updated') {
                bootstrap.Modal.getInstance(document.getElementById('editUserModal')).hide();
                showAlert('Пользователь успешно обновлен', 'success');
                window.loadUsers();
            } else {
                showAlert('Ошибка при редактировании пользователя', 'danger');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showAlert('Произошла ошибка', 'danger');
        }
    });

    // Обработка сброса пароля
    document.getElementById('confirmResetPassword').addEventListener('click', async () => {
        const userId = document.getElementById('resetPasswordModal').dataset.userId;
        try {
            const response = await fetch(`/api/admin/users/reset_pass/${userId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка сброса пароля');
            const result = await response.json();
            if (result.status === 'password_reset') {
                bootstrap.Modal.getInstance(document.getElementById('resetPasswordModal')).hide();
                showAlert('Пароль успешно сброшен', 'success');
                window.loadUsers();
            } else {
                showAlert('Ошибка при сбросе пароля', 'danger');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showAlert('Произошла ошибка', 'danger');
        }
    });

    // Привязка userId к модалу сброса пароля
    document.getElementById('resetPasswordModal').addEventListener('show.bs.modal', (event) => {
        const button = event.relatedTarget;
        document.getElementById('resetPasswordModal').dataset.userId = button.dataset.userId;
    });

    // Управление доступами к транспорту
    let availableParams = { uNumber: [], manager: [], region: [] };

    async function fetchAvailableParams() {
        try {
            const response = await fetch('/api/admin/users/get_transport_access_parameters', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка загрузки параметров');
            availableParams = await response.json();
        } catch (error) {
            console.error('Ошибка при загрузке параметров:', error);
            showAlert('Ошибка загрузки параметров доступа', 'danger');
        }
    }

    document.getElementById('userTransportAccessModal').addEventListener('show.bs.modal', async (event) => {
        const button = event.relatedTarget;
        const userId = button.dataset.userId;
        const accessRulesContainer = document.getElementById('accessRulesContainer');
        accessRulesContainer.innerHTML = '';

        try {
            const response = await fetch(`/api/admin/users/?id=${userId}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка загрузки данных пользователя');
            const [user] = await response.json();

            let rules = [];
            if (user.transport_access) {
                // Replace single quotes with double quotes
                const transportAccess = user.transport_access.replace(/'/g, '"');
                try {
                    rules = JSON.parse(transportAccess);
                } catch (parseError) {
                    console.error('Ошибка парсинга transport_access:', parseError, transportAccess);
                    showAlert('Неверный формат данных доступа', 'danger');
                    return;
                }
            }

            if (!availableParams.uNumber.length) await fetchAvailableParams();

            // Normalize rules
            const normalizedRules = rules.map(rule => ({
                type: rule.type || (rule.param === 'ALL' ? 'ALL' : rule.type || 'OR'),
                param: rule.param || 'region',
                value: rule.value || ''
            }));

            normalizedRules.forEach(rule => addAccessRule(rule));
        } catch (error) {
            console.error('Ошибка при загрузке правил:', error);
            showAlert('Ошибка загрузки правил доступа', 'danger');
        }

        document.getElementById('userTransportAccessModal').dataset.userId = userId;
    });

    document.getElementById('addAccessRule').addEventListener('click', () => {
        addAccessRule();
    });

    function addAccessRule(rule = { type: 'OR', param: 'region', value: '' }) {
        const accessRulesContainer = document.getElementById('accessRulesContainer');
        const template = document.getElementById('accessRuleTemplate').cloneNode(true);
        template.classList.remove('d-none');
        template.removeAttribute('id');

        const ruleRow = template.querySelector('.rule-row');
        const typeSelect = ruleRow.querySelector('.rule-type');
        const paramSelect = ruleRow.querySelector('.rule-param');
        const valueInput = ruleRow.querySelector('.rule-value');
        const suggestionsContainer = ruleRow.querySelector('.autocomplete-suggestions');
        const invalidIcon = ruleRow.querySelector('.invalid-value-icon');

        // Устанавливаем значения в новом порядке
        typeSelect.value = rule.type || 'OR';
        paramSelect.value = rule.type === 'ALL' ? 'ALL' : (rule.param || 'region');
        valueInput.value = rule.type === 'ALL' ? 'ALL' : (rule.value || '');

        // Отключаем поля при типе ALL
        if (rule.type === 'ALL') {
            paramSelect.value = 'ALL';
            valueInput.value = 'ALL';
            paramSelect.disabled = true;
            valueInput.disabled = true;
            suggestionsContainer.classList.add('d-none');
        }

        // Проверяем валидность значения
        checkValueAvailability(valueInput, paramSelect.value, invalidIcon);

        // Обработчик изменения типа правила
        typeSelect.addEventListener('change', () => {
            if (typeSelect.value === 'ALL') {
                paramSelect.value = 'ALL';
                valueInput.value = 'ALL';
                paramSelect.disabled = true;
                valueInput.disabled = true;
                suggestionsContainer.classList.add('d-none');
                invalidIcon.classList.add('d-none');
            } else {
                paramSelect.disabled = false;
                valueInput.disabled = false;
                paramSelect.value = 'region';
                valueInput.value = '';
                suggestionsContainer.classList.add('d-none');
                checkValueAvailability(valueInput, paramSelect.value, invalidIcon);
            }
        });

        // Обработчик изменения параметра
        paramSelect.addEventListener('change', () => {
            if (paramSelect.value !== 'ALL') {
                valueInput.value = '';
                suggestionsContainer.classList.add('d-none');
                checkValueAvailability(valueInput, paramSelect.value, invalidIcon);
            }
        });

        // Обработчик ввода в поле значения
        valueInput.addEventListener('input', () => {
            if (paramSelect.value !== 'ALL') {
                updateSuggestions(paramSelect.value, suggestionsContainer, valueInput.value);
                suggestionsContainer.classList.remove('d-none');
                checkValueAvailability(valueInput, paramSelect.value, invalidIcon);
            }
        });

        // Обработчик фокуса на поле значения
        valueInput.addEventListener('focus', () => {
            if (paramSelect.value !== 'ALL') {
                updateSuggestions(paramSelect.value, suggestionsContainer, valueInput.value);
                suggestionsContainer.classList.remove('d-none');
            }
        });

        // Обработчик потери фокуса
        valueInput.addEventListener('blur', () => {
            setTimeout(() => {
                suggestionsContainer.classList.add('d-none');
            }, 200);
        });

        // Обработчик клика по подсказке
        suggestionsContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion-item')) {
                valueInput.value = e.target.textContent;
                suggestionsContainer.classList.add('d-none');
                checkValueAvailability(valueInput, paramSelect.value, invalidIcon);
            }
        });

        // Обработчик удаления правила
        ruleRow.querySelector('.remove-rule').addEventListener('click', () => {
            ruleRow.remove();
        });

        accessRulesContainer.appendChild(ruleRow);
    }

    function updateSuggestions(param, suggestionsContainer, searchTerm = '') {
        suggestionsContainer.innerHTML = '';
        if (param === 'ALL') return;

        const values = availableParams[param] || [];

        // Фильтрация значений по подстроке (аналог LIKE '%ЗНАЧЕНИЕ%')
        const filteredValues = values
            .filter(value => value.toLowerCase().includes(searchTerm.toLowerCase()))
            .slice(0, 10);

        // Заполняем контейнер подсказок
        filteredValues.forEach(value => {
            const suggestionItem = document.createElement('div');
            suggestionItem.className = 'suggestion-item p-2 cursor-pointer hover:bg-light';
            suggestionItem.textContent = value;
            suggestionsContainer.appendChild(suggestionItem);
        });

        // Показываем или скрываем контейнер подсказок
        suggestionsContainer.classList.toggle('d-none', filteredValues.length === 0 || searchTerm === '');
    }

    function checkValueAvailability(input, param, invalidIcon) {
        if (param === 'ALL') {
            invalidIcon.classList.add('d-none');
            return;
        }
        const value = input.value;
        const isValid = !value || availableParams[param].includes(value);
        invalidIcon.classList.toggle('d-none', isValid);
    }

    document.getElementById('saveTransportAccess').addEventListener('click', async () => {
        const userId = document.getElementById('userTransportAccessModal').dataset.userId;
        const rules = [];
        const ruleRows = document.querySelectorAll('#accessRulesContainer .rule-row');

        ruleRows.forEach(row => {
            const type = row.querySelector('.rule-type').value;
            const param = type === 'ALL' ? 'ALL' : row.querySelector('.rule-param').value;
            const value = type === 'ALL' ? 'ALL' : row.querySelector('.rule-value').value;
            if (value || type === 'ALL') {
                rules.push({ type, param, value });
            }
        });

        try {
            const response = await fetch(`/api/admin/users/set_transport_access/${userId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ transport_access: rules }),
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка сохранения правил');
            const result = await response.json();
            if (result.status === 'transport_access_updated') {
                bootstrap.Modal.getInstance(document.getElementById('userTransportAccessModal')).hide();
                showAlert('Правила доступа успешно обновлены', 'success');
            } else {
                showAlert('Ошибка при сохранении правил доступа', 'danger');
            }
        } catch (error) {
            console.error('Ошибка при сохранении:', error);
            showAlert('Произошла ошибка при сохранении правил', 'danger');
        }
    });

    // Управление ролями функциональности
    let availableFunctionalityRoles = [];

    async function fetchAvailableFunctionalityRoles() {
        try {
            const response = await fetch('/api/admin/users/get_functionality_access_parameters', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка загрузки ролей функциональности');
            availableFunctionalityRoles = await response.json();
        } catch (error) {
            console.error('Ошибка при загрузке ролей функциональности:', error);
            showAlert('Ошибка загрузки ролей функциональности', 'danger');
        }
    }

    document.getElementById('userFunctionalityRolesModal').addEventListener('show.bs.modal', async (event) => {
        const button = event.relatedTarget;
        const userId = button.dataset.userId;
        const rolesContainer = document.getElementById('functionalityRolesContainer');
        rolesContainer.innerHTML = '';

        try {
            const response = await fetch(`/api/admin/users/?id=${userId}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка загрузки данных пользователя');
            const [user] = await response.json();

            let roles = [];
            if (user.functionality_roles) {
                try {
                    roles = user.functionality_roles;
                    if (typeof roles === 'string') {
                        roles = JSON.parse(roles.replace(/'/g, '"'));
                    }
                } catch (parseError) {
                    console.error('Ошибка парсинга functionality_roles:', parseError, user.functionality_roles);
                    showAlert('Неверный формат данных ролей функциональности', 'danger');
                    return;
                }
            }

            if (!availableFunctionalityRoles.length) await fetchAvailableFunctionalityRoles();

            // Группировка ролей по категориям
            const rolesByCategory = availableFunctionalityRoles.reduce((acc, role) => {
                if (!acc[role.category_localization]) {
                    acc[role.category_localization] = [];
                }
                acc[role.category_localization].push(role);
                return acc;
            }, {});

            // Сортировка категорий и ролей
            const sortedCategories = Object.keys(rolesByCategory).sort();
            sortedCategories.forEach(category => {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'mb-4';
                categoryDiv.innerHTML = `<h6 class="fw-bold mb-3">${category}</h6>`;

                const rolesList = document.createElement('div');
                rolesList.className = 'list-group';

                rolesByCategory[category]
                    .sort((a, b) => a.localization.localeCompare(b.localization))
                    .forEach(role => {
                        const isChecked = roles.includes(role.id) ? 'checked' : '';
                        rolesList.innerHTML += `
                            <label class="list-group-item d-flex align-items-center">
                                <input type="checkbox" class="form-check-input me-2 functionality-role-checkbox" value="${role.id}" ${isChecked}>
                                ${role.localization}
                            </label>
                        `;
                    });

                categoryDiv.appendChild(rolesList);
                rolesContainer.appendChild(categoryDiv);
            });

        } catch (error) {
            console.error('Ошибка при загрузке ролей:', error);
            showAlert('Ошибка загрузки ролей функциональности', 'danger');
        }

        document.getElementById('userFunctionalityRolesModal').dataset.userId = userId;
    });

    document.getElementById('saveFunctionalityRoles').addEventListener('click', async () => {
        const userId = document.getElementById('userFunctionalityRolesModal').dataset.userId;
        const roles = [];
        const checkboxes = document.querySelectorAll('#functionalityRolesContainer .functionality-role-checkbox:checked');

        checkboxes.forEach(checkbox => {
            roles.push(parseInt(checkbox.value));
        });

        try {
            const response = await fetch(`/api/admin/users/set_functionality_roles/${userId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ functionality_roles: roles.length ? roles : null }),
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Ошибка сохранения ролей');
            const result = await response.json();
            if (result.status === 'functionality_roles_updated') {
                bootstrap.Modal.getInstance(document.getElementById('userFunctionalityRolesModal')).hide();
                showAlert('Роли функциональности успешно обновлены', 'success');
            } else {
                showAlert('Ошибка при сохранении ролей функциональности', 'danger');
            }
        } catch (error) {
            console.error('Ошибка при сохранении:', error);
            showAlert('Произошла ошибка при сохранении ролей', 'danger');
        }
    });

    // Инициальная загрузка пользователей
    window.loadUsers();
});
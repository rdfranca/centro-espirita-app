// common.js

function validarCPF(cpf) {
    cpf = cpf.replace(/[^\d]+/g, '');
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;

    let soma = 0;
    for (let i = 0; i < 9; i++) {
        soma += parseInt(cpf.charAt(i)) * (10 - i);
    }
    let resto = (soma * 10) % 11;
    if (resto === 10 || resto === 11) resto = 0;
    if (resto !== parseInt(cpf.charAt(9))) return false;

    soma = 0;
    for (let i = 0; i < 10; i++) {
        soma += parseInt(cpf.charAt(i)) * (11 - i);
    }
    resto = (soma * 10) % 11;
    if (resto === 10 || resto === 11) resto = 0;
    if (resto !== parseInt(cpf.charAt(10))) return false;

    return true;
}

function aplicarMascaraCPF(campo) {
    campo.addEventListener('input', function () {
        let value = this.value.replace(/\D/g, '').slice(0, 11);
        if (value.length > 9)
            this.value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
        else if (value.length > 6)
            this.value = value.replace(/(\d{3})(\d{3})(\d{0,3})/, "$1.$2.$3");
        else if (value.length > 3)
            this.value = value.replace(/(\d{3})(\d{0,3})/, "$1.$2");
        else
            this.value = value;
    });
}

function aplicarMascaraCEP(campo) {
    campo.addEventListener('input', function () {
        let value = this.value.replace(/\D/g, '').slice(0, 8);
        if (value.length > 5)
            this.value = value.replace(/(\d{5})(\d{0,3})/, "$1-$2");
        else
            this.value = value;
    });
}

function togglePasswordVisibility(input, button) {
    if (input.type === 'password') {
        input.type = 'text';
        button.innerHTML = '🙈';
    } else {
        input.type = 'password';
        button.innerHTML = '👁️';
    }
}

function generateStrongPassword(length) {
    const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+~`|}{[]:;?><,./-=";
    let password = "";

    const types = [
        "abcdefghijklmnopqrstuvwxyz",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "0123456789",
        "!@#$%^&*()_+~`|}{[]:;?><,./-="
    ];

    for (let i = 0; i < types.length; i++) {
        password += getRandomChar(types[i]);
    }

    for (let i = types.length; i < length; i++) {
        password += getRandomChar(charset);
    }

    password = password.split('').sort(() => 0.5 - Math.random()).join('');

    return password;
}

function getRandomChar(charset) {
    return charset[Math.floor(Math.random() * charset.length)];
}

function atualizarDiasDaSemanaHidden(vinculoDiv) {
    const selectDias = vinculoDiv.querySelector('.dias-da-semana-select');
    const hiddenInput = vinculoDiv.querySelector('.dias-da-semana-hidden-input');
    if (selectDias && hiddenInput) {
        const selectedOptions = Array.from(selectDias.selectedOptions).map(option => option.value);
        hiddenInput.value = selectedOptions.join(',');
    }
}

// NOVO: Função para controlar a visibilidade do container de cursos
// Agora recebe idSetorEnsino e funcaoSetorMap para fazer a verificação baseada no SETOR
function setupCursosEnsinoVisibility(vinculosContainerId, cursosEnsinoContainerId, idSetorEnsino, funcaoSetorMap) {
    const vinculosContainer = document.getElementById(vinculosContainerId);
    const cursosEnsinoContainer = document.getElementById(cursosEnsinoContainerId);

    if (!vinculosContainer || !cursosEnsinoContainer) {
        console.warn("Containers de vínculos ou cursos de ensino não encontrados. Verifique os IDs.");
        return;
    }

    function checkSetorEnsinoVisibility() { // RENOMEADA para refletir a verificação por SETOR
        let setorEnsinoSelected = false;
        vinculosContainer.querySelectorAll('.funcao').forEach(selectFuncao => {
            const selectedFuncaoId = parseInt(selectFuncao.value);
            // Verifica se a função selecionada existe no nosso mapa e se o setor dela é o 'Ensino'
            if (funcaoSetorMap[selectedFuncaoId] === idSetorEnsino) {
                setorEnsinoSelected = true;
            }
        });

        if (setorEnsinoSelected) {
            cursosEnsinoContainer.style.display = 'block'; // Mostra o container de cursos
        } else {
            cursosEnsinoContainer.style.display = 'none';  // Oculta o container de cursos
            // Opcional: Desmarcar todos os cursos se nenhuma função do setor ensino estiver selecionada
            let selectCursos = cursosEnsinoContainer.querySelector('select[name="cursos_ensino[]"]');
            if (selectCursos) {
                Array.from(selectCursos.options).forEach(option => {
                    option.selected = false;
                });
            }
        }
    }

    // Chama a verificação inicial para o carregamento da página
    checkSetorEnsinoVisibility();

    // A função aplicarEventosVinculo (definida abaixo) será responsável por adicionar o listener de mudança de função.
}


// Função aplicarEventosVinculo (Completa e Única definição global)
function aplicarEventosVinculo(vinculo, setoresData) {
    const selectSetor = vinculo.querySelector('select[name="setores[]"]');
    const selectFuncao = vinculo.querySelector('select[name="funcoes[]"]');
    const selectDiasDaSemana = vinculo.querySelector('.dias-da-semana-select');
    const funcaoSelecionada = selectFuncao ? selectFuncao.getAttribute('data-selected') : null;

    // Popula setores se necessário (para novos blocos de vínculo)
    if (selectSetor && selectSetor.options.length <= 1 && setoresData) {
        setoresData.forEach(item => {
            const opt = document.createElement('option');
            opt.value = item.id;
            opt.textContent = item.nome;
            selectSetor.appendChild(opt);
        });
    }

    function carregarFuncoes(setorId, funcaoParaSelecionar = null) {
        if (!setorId) {
            selectFuncao.innerHTML = '<option disabled selected>Selecione o setor primeiro</option>';
            return;
        }
        fetch(`/api/funcoes_por_setor/${setorId}`)
            .then(res => res.json())
            .then(data => {
                selectFuncao.innerHTML = '<option disabled selected>Selecione a função</option>';
                data.forEach(item => {
                    const opt = document.createElement('option');
                    opt.value = item.id;
                    opt.textContent = item.nome;
                    if (funcaoParaSelecionar && item.id == funcaoParaSelecionar) {
                        opt.selected = true;
                    }
                    selectFuncao.appendChild(opt);
                });
                // NOVO: Após carregar as funções, reavalia a visibilidade dos cursos
                // Chama a função de checagem global se ela estiver disponível
                if (typeof checkSetorEnsinoVisibility === 'function') {
                    checkSetorEnsinoVisibility();
                }
            })
            .catch(err => console.error("Erro ao buscar funções:", err));
    }

    if (selectSetor && selectFuncao) {
        selectSetor.addEventListener('change', function () {
            carregarFuncoes(this.value);
        });

        // Carrega funções iniciais para o modo de edição
        if (selectSetor.value) {
            carregarFuncoes(selectSetor.value, funcaoSelecionada);
        }
    }

    // NOVO: Adiciona o listener para verificar a visibilidade dos cursos quando a função muda
    if (selectFuncao) {
        selectFuncao.addEventListener('change', () => {
            // Chama a função de checagem global se ela estiver disponível
            if (typeof checkSetorEnsinoVisibility === 'function') {
                checkSetorEnsinoVisibility();
            }
        });
    }

    if (selectDiasDaSemana) {
        selectDiasDaSemana.addEventListener('change', () => atualizarDiasDaSemanaHidden(vinculo));
        atualizarDiasDaSemanaHidden(vinculo);
    }

    const btnRemover = vinculo.querySelector('.remover-vinculo');
    if (btnRemover) {
        btnRemover.addEventListener('click', () => vinculo.remove());
    }
}

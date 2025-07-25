// common.js

// CPF, CEP e Senha (mesmos de antes)
function validarCPF(cpf) {
    cpf = cpf.replace(/[^\d]+/g, '');
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;

    let soma = 0;
    for (let i = 0; i < 9; i++) soma += parseInt(cpf.charAt(i)) * (10 - i);
    let resto = (soma * 10) % 11;
    if (resto === 10 || resto === 11) resto = 0;
    if (resto !== parseInt(cpf.charAt(9))) return false;

    soma = 0;
    for (let i = 0; i < 10; i++) soma += parseInt(cpf.charAt(i)) * (11 - i);
    resto = (soma * 10) % 11;
    if (resto === 10 || resto === 11) resto = 0;
    return resto === parseInt(cpf.charAt(10));
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
        else this.value = value;
    });
}

function aplicarMascaraCEP(campo) {
    campo.addEventListener('input', function () {
        let value = this.value.replace(/\D/g, '').slice(0, 8);
        if (value.length > 5)
            this.value = value.replace(/(\d{5})(\d{0,3})/, "$1-$2");
        else this.value = value;
    });
}

function togglePasswordVisibility(input, button) {
    input.type = input.type === 'password' ? 'text' : 'password';
    button.innerHTML = input.type === 'text' ? '🙈' : '👁️';
}

function generateStrongPassword(length) {
    const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+~`|}{[]:;?><,./-=";
    const types = [
        "abcdefghijklmnopqrstuvwxyz",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "0123456789",
        "!@#$%^&*()_+~`|}{[]:;?><,./-="
    ];
    let password = types.map(getRandomChar).join('');
    for (let i = types.length; i < length; i++) {
        password += getRandomChar(charset);
    }
    return password.split('').sort(() => 0.5 - Math.random()).join('');
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

// Variáveis globais para controlar a exibição de cursos
let globalFuncaoSetorMap = {};
let globalIdSetorEnsino = null;
let globalCursosEnsinoContainer = null;
let globalVinculosContainer = null;

// Tornada global
function checkSetorEnsinoVisibility() {
    let setorEnsinoSelected = false;
    globalVinculosContainer.querySelectorAll('.funcao').forEach(selectFuncao => {
        const selectedFuncaoId = parseInt(selectFuncao.value);
        if (globalFuncaoSetorMap[selectedFuncaoId] === globalIdSetorEnsino) {
            setorEnsinoSelected = true;
        }
    });

    if (globalCursosEnsinoContainer) {
        globalCursosEnsinoContainer.style.display = setorEnsinoSelected ? 'block' : 'none';
        if (!setorEnsinoSelected) {
            let selectCursos = globalCursosEnsinoContainer.querySelector('select[name="cursos_ensino[]"]');
            if (selectCursos) {
                Array.from(selectCursos.options).forEach(option => option.selected = false);
            }
        }
    }
}

// Atualizada com escuta de mudanças no SETOR também
function setupCursosEnsinoVisibility(vinculosContainerId, cursosEnsinoContainerId, idSetorEnsino, funcaoSetorMap) {
    globalVinculosContainer = document.getElementById(vinculosContainerId);
    globalCursosEnsinoContainer = document.getElementById(cursosEnsinoContainerId);
    globalIdSetorEnsino = idSetorEnsino;
    globalFuncaoSetorMap = funcaoSetorMap;

    if (!globalVinculosContainer || !globalCursosEnsinoContainer) {
        console.warn("Containers de vínculos ou cursos de ensino não encontrados.");
        return;
    }

    checkSetorEnsinoVisibility();

    // Adiciona escuta para mudanças de SETOR também, com pequeno delay para esperar o fetch
    globalVinculosContainer.querySelectorAll('.setor').forEach(selectSetor => {
        selectSetor.addEventListener('change', () => {
            setTimeout(() => {
                if (typeof checkSetorEnsinoVisibility === 'function') {
                    checkSetorEnsinoVisibility();
                }
            }, 300);
        });
    });

    globalVinculosContainer.addEventListener('change', checkSetorEnsinoVisibility);
}


// aplicarEventosVinculo completa
function aplicarEventosVinculo(vinculo, setoresData) {
    const selectSetor = vinculo.querySelector('select[name="setores[]"]');
    const selectFuncao = vinculo.querySelector('select[name="funcoes[]"]');
    const selectDiasDaSemana = vinculo.querySelector('.dias-da-semana-select');
    const funcaoSelecionada = selectFuncao ? selectFuncao.getAttribute('data-selected') : null;

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

        if (selectSetor.value) {
            carregarFuncoes(selectSetor.value, funcaoSelecionada);
        }
    }

    if (selectFuncao) {
        selectFuncao.addEventListener('change', () => {
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
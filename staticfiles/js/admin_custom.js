// MELHORIAS INTERATIVAS PARA O ADMIN - PharmaSys

document.addEventListener('DOMContentLoaded', function() {
    console.log('🎨 PharmaSys Admin Custom JS Carregado!');

    // 1. ADICIONAR ÍCONES AOS LABELS DOS CAMPOS
    const fieldIcons = {
        'id_nome': '📦 ',
        'id_codigo_barras': '📊 ',
        'id_preco_venda': '💰 ',
        'id_preco_compra': '💵 ',
        'id_categoria': '🏷️ ',
        'id_controlado': '⚠️ ',
        'id_fornecedor': '🏢 ',
        'id_estoque_minimo': '📦 ',
        'id_data_validade': '📅 ',
        'id_principio_ativo': '🧪 ',
        'id_dosagem': '💊 '
    };

    for (const fieldId in fieldIcons) {
        const field = document.getElementById(fieldId);
        if (field) {
            const label = document.querySelector(`label[for="${fieldId}"]`);
            if (label) {
                label.innerHTML = fieldIcons[fieldId] + label.innerHTML;
            }
        }
    }

    // 2. VALIDAÇÃO EM TEMPO REAL PARA PREÇOS
    const priceFields = document.querySelectorAll('#id_preco_venda, #id_preco_compra');
    priceFields.forEach(field => {
        field.addEventListener('input', function() {
            if (this.value < 0) {
                this.style.borderColor = '#ef4444';
                this.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.2)';
            } else {
                this.style.borderColor = '#22c55e';
                this.style.boxShadow = '0 0 0 3px rgba(34, 197, 94, 0.2)';
            }
        });
    });

    // 3. MENSAGEM DE BOAS-VINDAS DINÂMICA
    const header = document.querySelector('#header');
    if (header) {
        const welcomeMsg = document.createElement('div');
        welcomeMsg.innerHTML = '✨ PharmaSys Admin Personalizado';
        welcomeMsg.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
        welcomeMsg.style.color = 'white';
        welcomeMsg.style.padding = '8px 16px';
        welcomeMsg.style.borderRadius = '6px';
        welcomeMsg.style.margin = '10px 0';
        welcomeMsg.style.textAlign = 'center';
        welcomeMsg.style.fontWeight = 'bold';
        welcomeMsg.style.fontSize = '14px';
        header.appendChild(welcomeMsg);
    }

    // 4. DESTAQUE PARA CAMPOS OBRIGATÓRIOS
    const requiredFields = document.querySelectorAll('.required');
    requiredFields.forEach(field => {
        const label = field.querySelector('label');
        if (label) {
            label.style.color = '#dc2626';
            label.innerHTML = '🔴 ' + label.innerHTML;
        }
    });

    console.log('✅ Todas as melhorias visuais foram aplicadas!');
});
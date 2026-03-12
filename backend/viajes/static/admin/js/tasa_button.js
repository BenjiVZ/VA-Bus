// Admin JS for tasa BCV refresh button
(function() {
    document.addEventListener('DOMContentLoaded', function() {
        const submitRow = document.querySelector('.submit-row');
        if (submitRow && window.location.href.includes('configuraciongeneral')) {
            const btn = document.createElement('input');
            btn.type = 'submit';
            btn.name = '_actualizar_tasa';
            btn.value = '🔄 Actualizar Tasa BCV';
            btn.className = 'default';
            btn.style.cssText = 'background: #417690; float: left; margin-right: 10px;';
            submitRow.insertBefore(btn, submitRow.firstChild);
        }
    });
})();

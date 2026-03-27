// Auto show/hide "Viaje de Vuelta" fieldset based on tipo_viaje selection
(function() {
    'use strict';

    function toggleVuelta() {
        var tipo = document.getElementById('id_tipo_viaje');
        if (!tipo) return;

        // The "Viaje de Vuelta" fieldset has the collapse class
        var fieldsets = document.querySelectorAll('fieldset');
        var vueltaFieldset = null;

        fieldsets.forEach(function(fs) {
            var legend = fs.querySelector('h2');
            if (legend && legend.textContent.trim().indexOf('Viaje de Vuelta') !== -1) {
                vueltaFieldset = fs;
            }
        });

        if (!vueltaFieldset) return;

        if (tipo.value === 'ida_vuelta') {
            vueltaFieldset.style.display = '';
            vueltaFieldset.classList.remove('collapsed');
        } else {
            vueltaFieldset.style.display = 'none';
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        toggleVuelta();
        var tipo = document.getElementById('id_tipo_viaje');
        if (tipo) {
            tipo.addEventListener('change', toggleVuelta);
        }
    });
})();

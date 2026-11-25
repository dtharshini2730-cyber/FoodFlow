// FoodFlow ERP Client Scripts

document.addEventListener('DOMContentLoaded', function () {
    // Initialize Lucide icons if available
    if (window.lucide) {
        lucide.createIcons();
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 6000);
    });
});

// Production Form BOM fetch helper
function loadBOMVersionItems(versionId, targetTableBodyId) {
    if (!versionId) return;
    
    fetch('/production/bom-details/' + versionId)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById(targetTableBodyId);
            if (!tbody) return;
            
            tbody.innerHTML = '';
            const batchInput = document.getElementById('batch_count');
            const batchCount = batchInput ? parseFloat(batchInput.value) || 1 : 1;
            
            // Update expected output field
            const expectedOutputField = document.getElementById('expected_output_display');
            if (expectedOutputField) {
                expectedOutputField.innerText = (data.expected_output * batchCount) + ' pkts';
            }
            
            data.items.forEach(item => {
                const plannedQty = (item.standard_quantity * batchCount).toFixed(3);
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>
                        <strong>${item.name}</strong>
                        <input type="hidden" name="c_item_type[]" value="${item.item_type}">
                        <input type="hidden" name="c_item_id[]" value="${item.item_id}">
                        <input type="hidden" name="c_unit[]" value="${item.unit}">
                    </td>
                    <td>
                        <span class="badge bg-light text-dark">${item.item_type === 'raw_material' ? 'Raw Material' : 'Packaging'}</span>
                    </td>
                    <td>${plannedQty} ${item.unit}</td>
                    <td>
                        <input type="number" step="0.001" min="0" name="c_actual_qty[]" value="${plannedQty}" class="form-control form-control-sm actual-qty-input" required>
                    </td>
                    <td>
                        <input type="number" step="0.001" min="0" name="c_damaged_qty[]" value="0" class="form-control form-control-sm damaged-qty-input">
                    </td>
                    <td>${item.unit}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.error('Error loading recipe items:', err));
}

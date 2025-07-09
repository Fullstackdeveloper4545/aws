// Dashboard specific JavaScript

$(document).ready(function() {
    // Initialize DataTable for processes
    var processesTable = $('#processesTable').DataTable({
        responsive: true,
        pageLength: 25,
        order: [[4, 'desc']], // Sort by created date descending
        language: {
            search: "Search processes:",
            lengthMenu: "Show _MENU_ processes per page",
            info: "Showing _START_ to _END_ of _TOTAL_ processes",
            infoEmpty: "Showing 0 to 0 of 0 processes",
            infoFiltered: "(filtered from _MAX_ total processes)",
            paginate: {
                first: "First",
                last: "Last",
                next: "Next",
                previous: "Previous"
            }
        },
        columnDefs: [
            {
                targets: [0], // ID column
                width: '100px',
                className: 'text-monospace'
            },
            {
                targets: [2], // Status column
                width: '120px',
                orderable: true,
                searchable: true
            },
            {
                targets: [3], // S3 Location column
                width: '200px',
                className: 'text-truncate'
            },
            {
                targets: [4, 5], // Created and Updated columns
                width: '140px'
            },
            {
                targets: [6], // Actions column
                width: '120px',
                orderable: false,
                searchable: false
            }
        ]
    });

    // Refresh button functionality
    $('.btn-outline-secondary').on('click', function() {
        var $btn = $(this);
        if ($btn.text().includes('Refresh')) {
            $btn.prop('disabled', true);
            $btn.html('<i class="bi bi-arrow-clockwise spin"></i> Refreshing...');
            
            // Simulate refresh
            setTimeout(function() {
                location.reload();
            }, 1000);
        }
    });

    // Export button functionality
    $('.btn-outline-secondary').on('click', function() {
        var $btn = $(this);
        if ($btn.text().includes('Export')) {
            $btn.prop('disabled', true);
            $btn.html('<i class="bi bi-download"></i> Exporting...');
            
            // Export to CSV
            exportToCSV();
            
            setTimeout(function() {
                $btn.prop('disabled', false);
                $btn.html('Export');
            }, 2000);
        }
    });

    // Add row highlighting on hover
    $('#processesTable tbody').on('mouseenter', 'tr', function() {
        $(this).addClass('table-hover');
    }).on('mouseleave', 'tr', function() {
        $(this).removeClass('table-hover');
    });

    // Auto-refresh functionality (every 30 seconds)
    setInterval(function() {
        if (!document.hidden) {
            console.log('Auto-refresh check...');
        }
    }, 30000);

    // Add CSS for spinning animation
    if (!$('#spinner-css').length) {
        $('head').append('<style id="spinner-css">.spin { animation: spin 1s linear infinite; } @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>');
    }
});

// Export to CSV function
function exportToCSV() {
    var table = $('#processesTable').DataTable();
    var data = table.data().toArray();
    
    var csv = 'ID,Filename,Status,S3 Location,Created,Updated\n';
    
    data.forEach(function(row) {
        var csvRow = [];
        // Skip the last column (actions)
        for (var i = 0; i < row.length - 1; i++) {
            var cell = row[i] || '';
            
            // Clean up HTML tags from all columns
            cell = cell.replace(/<[^>]*>/g, '');
            
            // Trim whitespace
            cell = cell.trim();
            
            // Escape quotes and wrap in quotes if contains comma
            if (cell.toString().indexOf(',') !== -1 || cell.toString().indexOf('"') !== -1) {
                cell = '"' + cell.toString().replace(/"/g, '""') + '"';
            }
            csvRow.push(cell);
        }
        csv += csvRow.join(',') + '\n';
    });
    
    // Create download link
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var link = document.createElement('a');
    if (link.download !== undefined) {
        var url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', 'file_processes_' + new Date().toISOString().split('T')[0] + '.csv');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
} 
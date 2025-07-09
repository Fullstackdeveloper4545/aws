// Process detail specific JavaScript

$(document).ready(function() {
    // Initialize DataTable for API calls
    var apiCallsTable = $('#apiCallsTable').DataTable({
        responsive: true,
        pageLength: 50,
        order: [[0, 'asc']], // Sort by row number ascending
        language: {
            search: "Search API calls:",
            lengthMenu: "Show _MENU_ API calls per page",
            info: "Showing _START_ to _END_ of _TOTAL_ API calls",
            infoEmpty: "Showing 0 to 0 of 0 API calls",
            infoFiltered: "(filtered from _MAX_ total API calls)",
            emptyTable: "No API calls found",
            paginate: {
                first: "First",
                last: "Last",
                next: "Next",
                previous: "Previous"
            }
        },
        columnDefs: [
            {
                targets: [0], // Row number column
                width: '80px',
                className: 'text-center'
            },
            {
                targets: [1], // Status code column
                width: '100px',
                className: 'text-center',
                render: function(data, type, row) {
                    if (type === 'display') {
                        var statusClass = data >= 200 && data < 300 ? 'bg-success' : 'bg-danger';
                        return '<span class="badge ' + statusClass + '">' + data + '</span>';
                    }
                    return data;
                }
            },
            {
                targets: [2], // Status column
                width: '120px',
                className: 'text-center'
            },
            {
                targets: [3], // Response column
                width: '120px',
                className: 'text-center',
                orderable: false,
                searchable: false
            },
            {
                targets: [4], // Error message column
                width: '200px',
                className: 'text-truncate',
                render: function(data, type, row) {
                    if (type === 'display' && data && data.length > 50) {
                        return '<span title="' + data + '">' + data.substring(0, 50) + '...</span>';
                    }
                    return data;
                }
            },
            {
                targets: [5], // Created column
                width: '140px',
                render: function(data, type, row) {
                    if (type === 'display' && data) {
                        return moment(data).format('MMM D, YYYY HH:mm:ss');
                    }
                    return data;
                }
            },
            {
                targets: [6], // Actions column
                width: '100px',
                orderable: false,
                searchable: false,
                className: 'text-center'
            }
        ],
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        initComplete: function() {
            // Add custom filter for status codes
            this.api().columns(1).every(function() {
                var column = this;
                var select = $('<select class="form-select form-select-sm ms-2"><option value="">All Status Codes</option></select>')
                    .appendTo($('.dataTables_filter'))
                    .on('change', function() {
                        var val = $.fn.dataTable.util.escapeRegex($(this).val());
                        column.search(val ? '^' + val + '$' : '', true, false).draw();
                    });

                column.data().unique().sort().each(function(d, j) {
                    select.append('<option value="' + d + '">' + d + '</option>');
                });
            });
        }
    });

    // Modal functionality for viewing responses and payloads
    $('[data-bs-toggle="modal"]').on('click', function() {
        var target = $(this).data('bs-target');
        var modal = $(target);
        
        // Format JSON in modals
        modal.find('pre code').each(function() {
            try {
                var json = JSON.parse($(this).text());
                $(this).text(JSON.stringify(json, null, 2));
            } catch (e) {
                // Not JSON, leave as is
            }
        });
    });

    // Copy to clipboard functionality for modal content
    $('.modal-body pre').each(function() {
        var $pre = $(this);
        var $copyBtn = $('<button class="btn btn-sm btn-outline-secondary position-absolute top-0 end-0 m-2">' +
                        '<i class="bi bi-clipboard"></i> Copy</button>');
        
        $pre.css('position', 'relative');
        $pre.append($copyBtn);
        
        $copyBtn.on('click', function() {
            var text = $pre.find('code').text();
            navigator.clipboard.writeText(text).then(function() {
                $copyBtn.html('<i class="bi bi-check"></i> Copied!');
                setTimeout(function() {
                    $copyBtn.html('<i class="bi bi-clipboard"></i> Copy');
                }, 2000);
            });
        });
    });

    // Export functionality
    $('.btn-outline-secondary').on('click', function() {
        var $btn = $(this);
        if ($btn.text().includes('Export')) {
            $btn.prop('disabled', true);
            $btn.html('<i class="bi bi-download"></i> Exporting...');
            
            // Export to CSV
            exportApiCallsToCSV();
            
            setTimeout(function() {
                $btn.prop('disabled', false);
                $btn.html('Export');
            }, 2000);
        }
    });

    // Add row highlighting on hover
    $('#apiCallsTable tbody').on('mouseenter', 'tr', function() {
        $(this).addClass('table-hover');
    }).on('mouseleave', 'tr', function() {
        $(this).removeClass('table-hover');
    });

    // Keyboard shortcuts
    $(document).keydown(function(e) {
        // Ctrl/Cmd + E to export
        if ((e.ctrlKey || e.metaKey) && e.keyCode === 69) {
            e.preventDefault();
            $('.btn-outline-secondary').filter(function() {
                return $(this).text().includes('Export');
            }).click();
        }
        
        // Ctrl/Cmd + F to focus search
        if ((e.ctrlKey || e.metaKey) && e.keyCode === 70) {
            e.preventDefault();
            $('.dataTables_filter input').focus();
        }
    });

    // Auto-refresh functionality (every 60 seconds for API calls)
    setInterval(function() {
        if (!document.hidden) {
            // In a real application, you would make an AJAX call here
            // to check for new API calls and update the table
            console.log('Auto-refresh check for API calls...');
        }
    }, 60000);

    // Add CSS for better modal styling
    if (!$('#modal-css').length) {
        $('head').append('<style id="modal-css">' +
            '.modal-body pre { max-height: 400px; overflow-y: auto; }' +
            '.modal-body pre code { font-size: 0.875rem; line-height: 1.5; }' +
            '.position-absolute { z-index: 10; }' +
            '</style>');
    }
});

// Export API calls to CSV function
function exportApiCallsToCSV() {
    var table = $('#apiCallsTable').DataTable();
    var data = table.data().toArray();
    
    var csv = 'Row Number,Status Code,Status,Response,Error Message,Created\n';
    
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
        link.setAttribute('download', 'api_calls_' + new Date().toISOString().split('T')[0] + '.csv');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Utility function to format JSON for display
function formatJSON(jsonString) {
    try {
        var obj = JSON.parse(jsonString);
        return JSON.stringify(obj, null, 2);
    } catch (e) {
        return jsonString;
    }
}

// Real-time updates for API calls (for future implementation)
function setupApiCallsRealTimeUpdates() {
    // This would be implemented with WebSockets or Server-Sent Events
    // For now, it's just a placeholder
    console.log('Real-time updates for API calls not implemented yet');
}

// Performance monitoring for API calls table
function monitorApiCallsPerformance() {
    var startTime = performance.now();
    
    $('#apiCallsTable').on('draw.dt', function() {
        var endTime = performance.now();
        var renderTime = endTime - startTime;
        
        if (renderTime > 1000) {
            console.warn('API calls table render time:', renderTime + 'ms');
        }
        
        startTime = performance.now();
    });
}

// Initialize performance monitoring
monitorApiCallsPerformance(); 
// Dashboard specific JavaScript

$(document).ready(function() {
    // Initialize DataTable for processes with server-side processing
    var processesTable;
    
    try {
        processesTable = $('#processesTable').DataTable({
            processing: true,
            serverSide: true,
            ajax: {
                url: '/dashboard/api/processes/',
                type: 'GET',
                data: function(d) {
                    // Add filter parameters to the request
                    d.site_id = $('#siteIdFilter').val();
                    d.date_from = $('#dateFromFilter').val();
                    d.date_to = $('#dateToFilter').val();
                    d.status = $('#statusFilter').val();
                }
            },
            columns: [
                { data: 'id', name: 'id' },
                { data: 'site_id', name: 'site_id' },
                { data: 'filename', name: 'filename' },
                { 
                    data: 'status', 
                    name: 'status',
                    render: function(data, type, row) {
                        var badgeClass = '';
                        switch(data) {
                            case 'Processed':
                                badgeClass = 'bg-success';
                                break;
                            case 'Processing':
                                badgeClass = 'bg-info';
                                break;
                            case 'Failed':
                                badgeClass = 'bg-danger';
                                break;
                            case 'Pending':
                                badgeClass = 'bg-warning';
                                break;
                            default:
                                badgeClass = 'bg-secondary';
                        }
                        return '<span class="badge ' + badgeClass + '">' + data + '</span>';
                    }
                },
                { data: 'location', name: 'location' },
                { data: 'created_at', name: 'created_at' },
                { data: 'updated_at', name: 'updated_at' },
                { 
                    data: null,
                    name: 'actions',
                    orderable: false,
                    searchable: false,
                    render: function(data, type, row) {
                        return '<a href="' + row.detail_url + '" class="btn btn-sm btn-primary"><i class="bi bi-eye"></i> View Details</a>';
                    }
                }
            ],
            responsive: true,
            pageLength: 25,
            order: [[5, 'desc']], // Sort by created date descending
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
                },
                processing: "Loading data..."
            },
            columnDefs: [
                {
                    targets: [0], // ID column
                    width: '100px',
                    className: 'text-monospace'
                },
                {
                    targets: [1], // Site ID column
                    width: '120px',
                    className: 'text-monospace'
                },
                {
                    targets: [3], // Status column
                    width: '120px',
                    orderable: true,
                    searchable: true
                },
                {
                    targets: [4], // Location column
                    width: '200px',
                    className: 'text-truncate'
                },
                {
                    targets: [5, 6], // Created and Updated columns
                    width: '140px'
                },
                {
                    targets: [7], // Actions column
                    width: '120px',
                    orderable: false,
                    searchable: false
                }
            ]
        });
    } catch (error) {
        console.error('Error initializing DataTable:', error);
    }

    // Add CSS for spinning animation (only once)
    if (!$('#spinner-css').length) {
        $('head').append('<style id="spinner-css">.spin { animation: spin 1s linear infinite; } @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>');
    }

    // Filter form submission
    $('#applyFilters').on('click', function(e) {
        e.preventDefault();
        if (processesTable) {
            processesTable.ajax.reload();
        }else{
            console.log('No processes table found');
        }
    });

    // Clear filters button
    $('#clearFilters').on('click', function() {
        $('#siteIdFilter').val('');
        $('#dateFromFilter').val('');
        $('#dateToFilter').val('');
        $('#statusFilter').val('');
        if (processesTable) {
            processesTable.ajax.reload();
        }else{
            console.log('No processes table found');
        }
    });

    // Refresh button functionality
    $('#refreshBtn').on('click', function() {
        var $btn = $(this);
        $btn.prop('disabled', true);
        $btn.html('<i class="bi bi-arrow-clockwise spin"></i> Refreshing...');
        
        if (processesTable) {
            processesTable.ajax.reload(function() {
                $btn.prop('disabled', false);
                $btn.html('Refresh');
            });
        } else {
            setTimeout(function() {
                $btn.prop('disabled', false);
                $btn.html('Refresh');
            }, 1000);
        }
    });

    // Export button functionality
    $('#exportBtn').on('click', function() {
        var $btn = $(this);
        $btn.prop('disabled', true);
        $btn.html('<i class="bi bi-download"></i> Exporting...');
        
        try {
            // Export to CSV with current filters
            exportToCSV();
        } catch (error) {
            console.error('Error exporting CSV:', error);
            alert('Error exporting data. Please try again.');
        }
        
        setTimeout(function() {
            $btn.prop('disabled', false);
            $btn.html('Export');
        }, 2000);
    });

    // Add row highlighting on hover
    $('#processesTable tbody').on('mouseenter', 'tr', function() {
        $(this).addClass('table-hover');
    }).on('mouseleave', 'tr', function() {
        $(this).removeClass('table-hover');
    });
});

// Export to CSV function with current filters
function exportToCSV() {
    try {
        // Get current filter values
        var siteId = $('#siteIdFilter').val();
        var dateFrom = $('#dateFromFilter').val();
        var dateTo = $('#dateToFilter').val();
        var status = $('#statusFilter').val();
        
        // Build export URL with filters
        var exportUrl = '/dashboard/api/processes/?export=csv';
        if (siteId) exportUrl += '&site_id=' + encodeURIComponent(siteId);
        if (dateFrom) exportUrl += '&date_from=' + encodeURIComponent(dateFrom);
        if (dateTo) exportUrl += '&date_to=' + encodeURIComponent(dateTo);
        if (status) exportUrl += '&status=' + encodeURIComponent(status);
        
        // Create download link
        var link = document.createElement('a');
        link.setAttribute('href', exportUrl);
        link.setAttribute('download', 'file_processes_' + new Date().toISOString().split('T')[0] + '.csv');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
    } catch (error) {
        console.error('Error exporting CSV:', error);
        throw error;
    }
} 
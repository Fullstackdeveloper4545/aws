// User Management specific JavaScript

$(document).ready(function() {
    // Initialize DataTable for users with server-side processing
    var usersTable;
    
    try {
        usersTable = $('#usersTable').DataTable({
            processing: true,
            serverSide: true,
            ajax: {
                url: '/account/api/users/',
                type: 'GET',
                data: function(d) {
                    // Add filter parameters to the request
                    d.status = $('#statusFilter').val();
                    d.search = $('#searchFilter').val();
                }
            },
            columns: [
                { data: 'id', name: 'id' },
                { data: 'email', name: 'email' },
                { data: 'full_name', name: 'full_name' },
                { 
                    data: 'status', 
                    name: 'status',
                    render: function(data, type, row) {
                        var badgeClass = data === 'Active' ? 'bg-success' : 'bg-warning';
                        return '<span class="badge ' + badgeClass + '">' + data + '</span>';
                    }
                },
                { 
                    data: 'user_access', 
                    name: 'user_access',
                    render: function(data, type, row) {
                        var badgeClass = data === 'Yes' ? 'bg-info' : 'bg-secondary';
                        return '<span class="badge ' + badgeClass + '">' + data + '</span>';
                    }
                },
                { data: 'date_joined', name: 'date_joined' },
                { data: 'last_login', name: 'last_login' },
                { 
                    data: null,
                    name: 'actions',
                    orderable: false,
                    searchable: false,
                    render: function(data, type, row) {
                        var buttons = '<div class="btn-group" role="group">';
                        buttons += '<a href="' + row.edit_url + '" class="btn btn-sm btn-primary me-1"><i class="bi bi-pencil"></i> Edit</a>';
                        

                        

                        buttons += '</div>';
                        
                        return buttons;
                    }
                }
            ],
            responsive: true,
            pageLength: 25,
            order: [[5, 'desc']], // Sort by date joined descending
            language: {
                search: "Search users:",
                lengthMenu: "Show _MENU_ users per page",
                info: "Showing _START_ to _END_ of _TOTAL_ users",
                infoEmpty: "Showing 0 to 0 of 0 users",
                infoFiltered: "(filtered from _MAX_ total users)",
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
                    width: '80px',
                    className: 'text-monospace'
                },
                {
                    targets: [1], // Email column
                    width: '200px',
                    className: 'text-monospace'
                },
                {
                    targets: [2], // Full Name column
                    width: '150px'
                },
                {
                    targets: [3], // Status column
                    width: '100px',
                    orderable: true,
                    searchable: true
                },
                {
                    targets: [4], // User Management column
                    width: '120px',
                    orderable: true,
                    searchable: true
                },
                {
                    targets: [5, 6], // Date columns
                    width: '140px'
                },
                {
                    targets: [7], // Actions column
                    width: '200px',
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
        if (usersTable) {
            usersTable.ajax.reload();
        } else {
            console.log('No users table found');
        }
    });

    // Clear filters button
    $('#clearFilters').on('click', function() {
        $('#statusFilter').val('');
        $('#searchFilter').val('');
        if (usersTable) {
            usersTable.ajax.reload();
        } else {
            console.log('No users table found');
        }
    });

    // Refresh button functionality
    $('#refreshBtn').on('click', function() {
        var $btn = $(this);
        $btn.prop('disabled', true);
        $btn.html('<i class="bi bi-arrow-clockwise spin"></i> Refreshing...');
        
        if (usersTable) {
            usersTable.ajax.reload(function() {
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
    $('#usersTable tbody').on('mouseenter', 'tr', function() {
        $(this).addClass('table-hover');
    }).on('mouseleave', 'tr', function() {
        $(this).removeClass('table-hover');
    });
});



// Export to CSV function with current filters
function exportToCSV() {
    try {
        // Get current filter values
        var status = $('#statusFilter').val();
        var search = $('#searchFilter').val();
        
        // Build export URL with filters
        var exportUrl = '/account/api/users/?export=csv';
        if (status) exportUrl += '&status=' + encodeURIComponent(status);
        if (search) exportUrl += '&search=' + encodeURIComponent(search);
        
        // Create download link
        var link = document.createElement('a');
        link.setAttribute('href', exportUrl);
        link.setAttribute('download', 'users_' + new Date().toISOString().split('T')[0] + '.csv');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
    } catch (error) {
        console.error('Error exporting CSV:', error);
        throw error;
    }
}

// Form validation for user add/edit pages
$(document).ready(function() {
    // Add Bootstrap classes to form fields
    $('input[type="text"], input[type="email"], input[type="password"], select').addClass('form-control');
    $('input[type="checkbox"]').addClass('form-check-input');
    
    // Real-time validation
    $('form').on('submit', function(e) {
        var isValid = true;
        
        // Check required fields
        $(this).find('input[required], select[required]').each(function() {
            if (!$(this).val()) {
                $(this).addClass('is-invalid');
                isValid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        // Check password confirmation
        var password1 = $('input[name="password1"]');
        var password2 = $('input[name="password2"]');
        
        if (password1.length && password2.length) {
            if (password1.val() !== password2.val()) {
                password2.addClass('is-invalid');
                isValid = false;
            } else {
                password2.removeClass('is-invalid');
            }
        }
        
        if (!isValid) {
            e.preventDefault();
            alert('Please correct the errors before submitting.');
        }
    });
    
    // Remove validation classes on input
    $('input, select').on('input change', function() {
        $(this).removeClass('is-invalid');
    });
});

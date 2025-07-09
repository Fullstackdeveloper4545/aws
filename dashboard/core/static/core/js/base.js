// Base JavaScript for the dashboard

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Sidebar toggle for mobile
    $('.navbar-toggler').on('click', function(e) {
        e.preventDefault();
        $('.sidebar').toggleClass('show');
        
        // Add/remove overlay
        if ($(window).width() < 768) {
            if ($('.sidebar').hasClass('show')) {
                if ($('.sidebar-overlay').length === 0) {
                    $('body').append('<div class="sidebar-overlay"></div>');
                }
                $('.sidebar-overlay').addClass('show');
            } else {
                $('.sidebar-overlay').removeClass('show');
            }
        }
    });

    // Close sidebar when clicking overlay
    $(document).on('click', '.sidebar-overlay', function() {
        $('.sidebar').removeClass('show');
        $('.sidebar-overlay').removeClass('show');
    });

    // Handle window resize
    $(window).on('resize', function() {
        if ($(window).width() >= 768) {
            $('.sidebar').removeClass('show');
            $('.sidebar-overlay').removeClass('show');
        }
    });

    // Add loading state to buttons
    $('.btn').on('click', function() {
        var $btn = $(this);
        if (!$btn.hasClass('btn-loading')) {
            $btn.addClass('btn-loading');
            $btn.prop('disabled', true);
            
            // Remove loading state after 2 seconds (for demo purposes)
            setTimeout(function() {
                $btn.removeClass('btn-loading');
                $btn.prop('disabled', false);
            }, 2000);
        }
    });

    // Auto-hide alerts after 5 seconds
    $('.alert').each(function() {
        var $alert = $(this);
        setTimeout(function() {
            $alert.fadeOut();
        }, 5000);
    });

    // Confirm delete actions
    $('[data-confirm]').on('click', function(e) {
        var message = $(this).data('confirm');
        if (!confirm(message)) {
            e.preventDefault();
            return false;
        }
    });

    // Format timestamps
    $('.timestamp').each(function() {
        var timestamp = $(this).text();
        if (timestamp) {
            var date = new Date(timestamp);
            $(this).text(date.toLocaleString());
        }
    });

    // Copy to clipboard functionality
    $('.copy-to-clipboard').on('click', function(e) {
        e.preventDefault();
        var text = $(this).data('clipboard-text');
        navigator.clipboard.writeText(text).then(function() {
            // Show success message
            var $btn = $(e.target);
            var originalText = $btn.text();
            $btn.text('Copied!');
            setTimeout(function() {
                $btn.text(originalText);
            }, 2000);
        });
    });

    // Responsive table wrapper
    $('.table-responsive').each(function() {
        var $table = $(this);
        var $tableElement = $table.find('table');
        
        if ($tableElement.width() > $table.width()) {
            $table.addClass('has-scroll');
        }
    });

    // Smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function(e) {
        e.preventDefault();
        var target = $(this.getAttribute('href'));
        if (target.length) {
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 100
            }, 1000);
        }
    });

    // Initialize any custom components
    initializeCustomComponents();
});

// Custom components initialization
function initializeCustomComponents() {
    // Add any custom component initialization here
    
    // Example: Custom dropdown behavior
    $('.custom-dropdown').on('click', function(e) {
        e.preventDefault();
        $(this).next('.dropdown-menu').toggleClass('show');
    });

    // Example: Custom modal behavior
    $('.custom-modal-trigger').on('click', function(e) {
        e.preventDefault();
        var modalId = $(this).data('modal-target');
        $('#' + modalId).modal('show');
    });
}

// Utility functions
window.DashboardUtils = {
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        var k = 1024;
        var sizes = ['Bytes', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Format date
    formatDate: function(date) {
        return new Date(date).toLocaleDateString();
    },

    // Format datetime
    formatDateTime: function(date) {
        return new Date(date).toLocaleString();
    },

    // Show notification
    showNotification: function(message, type) {
        type = type || 'info';
        var alertClass = 'alert-' + type;
        var alertHtml = '<div class="alert ' + alertClass + ' alert-dismissible fade show" role="alert">' +
                       message +
                       '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
                       '</div>';
        
        $('.notifications-container').append(alertHtml);
        
        // Auto-hide after 5 seconds
        setTimeout(function() {
            $('.notifications-container .alert').last().fadeOut();
        }, 5000);
    },

    // Debounce function
    debounce: function(func, wait, immediate) {
        var timeout;
        return function() {
            var context = this, args = arguments;
            var later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            var callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    }
};

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    DashboardUtils.showNotification('An error occurred. Please try again.', 'danger');
});

// AJAX error handler
$(document).ajaxError(function(event, xhr, settings, error) {
    console.error('AJAX error:', error);
    DashboardUtils.showNotification('Network error. Please check your connection.', 'danger');
}); 
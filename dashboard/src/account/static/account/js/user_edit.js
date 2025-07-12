// User Edit specific JavaScript

$(document).ready(function() {
    // Add Bootstrap classes to form fields
    $('input[type="text"], input[type="email"]').addClass('form-control');
    $('input[type="checkbox"]').addClass('form-check-input');
    
    // Real-time validation
    $('form').on('submit', function(e) {
        var isValid = true;
        
        // Check required fields
        $(this).find('input[required]').each(function() {
            if (!$(this).val()) {
                $(this).addClass('is-invalid');
                isValid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        // Email format validation
        var email = $('input[name="email"]').val();
        if (email) {
            var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                $('input[name="email"]').addClass('is-invalid');
                isValid = false;
            } else {
                $('input[name="email"]').removeClass('is-invalid');
            }
        }
        
        // Password validation
        var newPassword = $('#newPassword').val();
        var confirmPassword = $('#confirmPassword').val();
        
        if (newPassword || confirmPassword) {
            // If one password field is filled, both must be filled
            if (!newPassword) {
                $('#newPassword').addClass('is-invalid');
                $('#newPassword').next('.invalid-feedback').remove();
                $('#newPassword').after('<div class="invalid-feedback">Please enter a new password.</div>');
                isValid = false;
            } else {
                $('#newPassword').removeClass('is-invalid');
                $('#newPassword').next('.invalid-feedback').remove();
            }
            
            if (!confirmPassword) {
                $('#confirmPassword').addClass('is-invalid');
                $('#confirmPassword').next('.invalid-feedback').remove();
                $('#confirmPassword').after('<div class="invalid-feedback">Please confirm the new password.</div>');
                isValid = false;
            } else {
                $('#confirmPassword').removeClass('is-invalid');
                $('#confirmPassword').next('.invalid-feedback').remove();
            }
            
            // Check if passwords match
            if (newPassword && confirmPassword && newPassword !== confirmPassword) {
                $('#confirmPassword').addClass('is-invalid');
                $('#confirmPassword').next('.invalid-feedback').remove();
                $('#confirmPassword').after('<div class="invalid-feedback">Passwords do not match.</div>');
                isValid = false;
            }
            
            // Check password strength if password is provided
            if (newPassword) {
                var hasMinLength = newPassword.length >= 8;
                var hasUpperCase = /[A-Z]/.test(newPassword);
                var hasLowerCase = /[a-z]/.test(newPassword);
                var hasNumbers = /\d/.test(newPassword);
                var hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(newPassword);
                
                if (!hasMinLength || !hasUpperCase || !hasLowerCase || !hasNumbers || !hasSpecialChar) {
                    $('#newPassword').addClass('is-invalid');
                    $('#newPassword').next('.invalid-feedback').remove();
                    $('#newPassword').after('<div class="invalid-feedback">Password must meet all requirements.</div>');
                    isValid = false;
                } else {
                    $('#newPassword').removeClass('is-invalid');
                    $('#newPassword').next('.invalid-feedback').remove();
                }
            }
        }
        
        if (!isValid) {
            e.preventDefault();
            alert('Please correct the errors before submitting.');
        } else {
            // Show loading state
            $(this).addClass('form-submitting');
            $('button[type="submit"]').prop('disabled', true).html('<i class="bi bi-hourglass-split spin"></i> Updating User...');
        }
    });
    
    // Remove validation classes on input
    $('input').on('input', function() {
        $(this).removeClass('is-invalid');
    });
    
    // Email availability check (only if changed)
    var originalEmail = $('input[name="email"]').val();
    var emailTimeout;
    $('input[name="email"]').on('input', function() {
        clearTimeout(emailTimeout);
        var email = $(this).val();
        var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        // Only check availability if it's a valid email format, has at least 3 characters, and is different from original
        if (email !== originalEmail && email.length >= 3 && emailRegex.test(email)) {
            emailTimeout = setTimeout(function() {
                checkEmailAvailability(email);
            }, 500);
        } else if (email === originalEmail) {
            $(this).removeClass('is-invalid is-valid');
            $(this).siblings('.invalid-feedback, .valid-feedback').remove();
        } else {
            // Clear any existing availability feedback if not a valid email
            var input = $(this);
            input.siblings('.valid-feedback').remove();
            input.removeClass('is-valid');
        }
    });
    
    // Email format validation
    $('input[name="email"]').on('input', function() {
        var email = $(this).val();
        var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (email && !emailRegex.test(email)) {
            $(this).addClass('is-invalid');
            $(this).next('.invalid-feedback').remove();
            $(this).after('<div class="invalid-feedback">Please enter a valid email address.</div>');
        } else {
            $(this).removeClass('is-invalid');
            $(this).next('.invalid-feedback').remove();
        }
    });
    
    // Auto-capitalize first and last names
    $('input[name="first_name"], input[name="last_name"]').on('input', function() {
        var value = $(this).val();
        if (value) {
            $(this).val(value.charAt(0).toUpperCase() + value.slice(1).toLowerCase());
        }
    });
    
    // Status change confirmation
    $('input[name="is_active"]').on('change', function() {
        var isChecked = $(this).is(':checked');
        var email = $('input[name="email"]').val();
        var action = isChecked ? 'activate' : 'deactivate';
        
        if (!confirm('Are you sure you want to ' + action + ' user "' + email + '"?')) {
            $(this).prop('checked', !isChecked);
        }
    });
    
    // Show user status indicator
    updateStatusIndicator();
    
    // Update status indicator when checkbox changes
    $('input[name="is_active"]').on('change', function() {
        updateStatusIndicator();
    });
    
    // Password strength indicator
    $('#newPassword').on('input', function() {
        var password = $(this).val();
        var hasMinLength = password.length >= 8;
        var hasUpperCase = /[A-Z]/.test(password);
        var hasLowerCase = /[a-z]/.test(password);
        var hasNumbers = /\d/.test(password);
        var hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        
        // Create checklist HTML
        var checklist = '<div class="password-checklist mt-2">';
        checklist += '<div class="form-text mb-2"><strong>Password Requirements:</strong></div>';
        checklist += '<div class="requirement-item ' + (hasMinLength ? 'text-success' : 'text-muted') + '">';
        checklist += '<i class="bi ' + (hasMinLength ? 'bi-check-circle-fill' : 'bi-circle') + ' me-2"></i>';
        checklist += 'At least 8 characters';
        checklist += '</div>';
        checklist += '<div class="requirement-item ' + (hasUpperCase ? 'text-success' : 'text-muted') + '">';
        checklist += '<i class="bi ' + (hasUpperCase ? 'bi-check-circle-fill' : 'bi-circle') + ' me-2"></i>';
        checklist += 'At least one uppercase letter (A-Z)';
        checklist += '</div>';
        checklist += '<div class="requirement-item ' + (hasLowerCase ? 'text-success' : 'text-muted') + '">';
        checklist += '<i class="bi ' + (hasLowerCase ? 'bi-check-circle-fill' : 'bi-circle') + ' me-2"></i>';
        checklist += 'At least one lowercase letter (a-z)';
        checklist += '</div>';
        checklist += '<div class="requirement-item ' + (hasNumbers ? 'text-success' : 'text-muted') + '">';
        checklist += '<i class="bi ' + (hasNumbers ? 'bi-check-circle-fill' : 'bi-circle') + ' me-2"></i>';
        checklist += 'At least one number (0-9)';
        checklist += '</div>';
        checklist += '<div class="requirement-item ' + (hasSpecialChar ? 'text-success' : 'text-muted') + '">';
        checklist += '<i class="bi ' + (hasSpecialChar ? 'bi-check-circle-fill' : 'bi-circle') + ' me-2"></i>';
        checklist += 'At least one special character (!@#$%^&*(),.?":{}|<>)';
        checklist += '</div>';
        checklist += '</div>';
        
        // Remove existing feedback
        $(this).next('.password-checklist').remove();
        $(this).after(checklist);
    });
    
    // Clear password fields on input
    $('#newPassword, #confirmPassword').on('input', function() {
        $(this).removeClass('is-invalid');
        $(this).next('.invalid-feedback').remove();
    });
});

// Function to check email availability
function checkEmailAvailability(email) {
    $.ajax({
        url: '/account/api/check-email/',
        type: 'GET',
        data: { email: email },
        success: function(response) {
            var input = $('input[name="email"]');
            // Remove all existing feedback messages
            input.siblings('.invalid-feedback, .valid-feedback').remove();
            
            if (response.available) {
                input.removeClass('is-invalid').addClass('is-valid');
                input.after('<div class="valid-feedback">Email is available!</div>');
            } else {
                input.removeClass('is-valid').addClass('is-invalid');
                input.after('<div class="invalid-feedback">Email is already taken.</div>');
            }
        },
        error: function() {
            // If check fails, don't show any feedback
            console.log('Email availability check failed');
        }
    });
}

// Function to update status indicator
function updateStatusIndicator() {
    var isActive = $('input[name="is_active"]').is(':checked');
    var statusText = isActive ? 'Active' : 'Inactive';
    var statusClass = isActive ? 'status-active' : 'status-inactive';
    
    // Remove existing status indicator
    $('.status-indicator').remove();
    
    // Add new status indicator
    var indicator = '<div class="status-indicator ' + statusClass + ' mt-2"><i class="bi bi-circle-fill me-2"></i>' + statusText + '</div>';
    $('input[name="is_active"]').closest('.form-group').append(indicator);
}

// Form reset functionality
function resetForm() {
    $('form')[0].reset();
    $('input').removeClass('is-invalid is-valid');
    $('.invalid-feedback, .valid-feedback, .password-checklist').remove();
    $('button[type="submit"]').prop('disabled', false).html('<i class="bi bi-check-circle me-2"></i>Update User');
    $('form').removeClass('form-submitting');
    updateStatusIndicator();
}

// Keyboard shortcuts
$(document).keydown(function(e) {
    // Ctrl+Enter to submit form
    if (e.ctrlKey && e.keyCode === 13) {
        $('form').submit();
    }
    
    // Escape to reset form
    if (e.keyCode === 27) {
        resetForm();
    }
});

// Show user information summary
function showUserSummary() {
    var email = $('input[name="email"]').val();
    var firstName = $('input[name="first_name"]').val();
    var lastName = $('input[name="last_name"]').val();
    var isActive = $('input[name="is_active"]').is(':checked');
    
    var summary = '<div class="user-info mt-3">';
    summary += '<h6><i class="bi bi-person-circle me-2"></i>User Summary</h6>';
    summary += '<p><strong>Email:</strong> ' + (email || 'Not set') + '</p>';
    summary += '<p><strong>Full Name:</strong> ' + (firstName + ' ' + lastName).trim() || 'Not set' + '</p>';
    summary += '<p><strong>Status:</strong> ' + (isActive ? 'Active' : 'Inactive') + '</p>';
    summary += '</div>';
    
    // Remove existing summary
    $('.user-info').remove();
    
    // Add new summary
    $('form').append(summary);
}

// Update summary when form changes
$('input').on('input change', function() {
    showUserSummary();
});

// Initial summary
showUserSummary();



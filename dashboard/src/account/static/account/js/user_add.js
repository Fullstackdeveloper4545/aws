// User Add specific JavaScript

$(document).ready(function() {
    // Add Bootstrap classes to form fields
    $('input[type="text"], input[type="email"], input[type="password"]').addClass('form-control');
    
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
        
        // Check password strength
        if (password1.length && password1.val()) {
            var password = password1.val();
            var hasMinLength = password.length >= 8;
            var hasUpperCase = /[A-Z]/.test(password);
            var hasLowerCase = /[a-z]/.test(password);
            var hasNumbers = /\d/.test(password);
            var hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
            
            if (!hasMinLength || !hasUpperCase || !hasLowerCase || !hasNumbers || !hasSpecialChar) {
                password1.addClass('is-invalid');
                isValid = false;
            } else {
                password1.removeClass('is-invalid');
            }
        }
        
        if (!isValid) {
            e.preventDefault();
            alert('Please correct the errors before submitting.');
        } else {
            // Show loading state
            $(this).addClass('form-submitting');
            $('button[type="submit"]').prop('disabled', true).html('<i class="bi bi-hourglass-split spin"></i> Creating User...');
        }
    });
    
    // Remove validation classes on input
    $('input').on('input', function() {
        $(this).removeClass('is-invalid');
    });
    
    // Password strength indicator with visual checklist
    $('input[name="password1"]').on('input', function() {
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
    
    // Email availability check
    var emailTimeout;
    $('input[name="email"]').on('input', function() {
        clearTimeout(emailTimeout);
        var email = $(this).val();
        
        if (email.length >= 3) {
            emailTimeout = setTimeout(function() {
                checkEmailAvailability(email);
            }, 500);
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
});

// Function to check email availability
function checkEmailAvailability(email) {
    $.ajax({
        url: '/account/api/check-email/',
        type: 'GET',
        data: { email: email },
        success: function(response) {
            var input = $('input[name="email"]');
            if (response.available) {
                input.removeClass('is-invalid').addClass('is-valid');
                input.next('.invalid-feedback, .valid-feedback').remove();
                input.after('<div class="valid-feedback">Email is available!</div>');
            } else {
                input.removeClass('is-valid').addClass('is-invalid');
                input.next('.invalid-feedback, .valid-feedback').remove();
                input.after('<div class="invalid-feedback">Email is already taken.</div>');
            }
        },
        error: function() {
            // If check fails, don't show any feedback
            console.log('Email availability check failed');
        }
    });
}

// Form reset functionality
function resetForm() {
    $('form')[0].reset();
    $('input').removeClass('is-invalid is-valid');
    $('.invalid-feedback, .valid-feedback, .form-text, .password-checklist').remove();
    $('button[type="submit"]').prop('disabled', false).html('<i class="bi bi-person-plus me-2"></i>Create User');
    $('form').removeClass('form-submitting');
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

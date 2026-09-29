/**
 * Kabale University IDR Enhanced Research Discovery Platform
 * Client-side utilities and interactive enhancements
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el));

    // Copy handle to clipboard
    const copyBtns = document.querySelectorAll('.copy-handle-btn');
    copyBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const handleText = btn.getAttribute('data-handle');
            if (handleText) {
                navigator.clipboard.writeText(handleText).then(() => {
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '<i class="bi bi-check2"></i> Copied!';
                    btn.classList.remove('btn-outline-secondary');
                    btn.classList.add('btn-success');
                    setTimeout(() => {
                        btn.innerHTML = originalText;
                        btn.classList.remove('btn-success');
                        btn.classList.add('btn-outline-secondary');
                    }, 2000);
                });
            }
        });
    });
});

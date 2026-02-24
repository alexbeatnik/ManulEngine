// dom_utils.js
const getInteractiveElements = () => {
    const selector = 'button, a, input, [role="button"], textarea, select';
    const elements = document.querySelectorAll(selector);
    
    return Array.from(elements)
        .filter(el => {
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        })
        .map((el, index) => {
            el.setAttribute('data-ai-id', index);
            return {
                id: index,
                tag: el.tagName.toLowerCase(),
                text: el.innerText?.trim() || el.placeholder || el.ariaLabel || "no text",
                type: el.type || "N/A"
            };
        });
};
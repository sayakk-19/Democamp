(function () {
    'use strict';
    const dialog = document.getElementById('store-search-dialog');
    if (!dialog || typeof dialog.showModal !== 'function') return;
    const input = document.getElementById('store-search-input');
    const list = document.getElementById('store-search-suggestions');
    const status = dialog.querySelector('[data-store-search-status]');
    const clear = dialog.querySelector('[data-store-search-clear]');
    const correction = dialog.querySelector('[data-store-search-correction]');
    const shop = dialog.querySelector('[data-store-search-shop]');
    const triggers = document.querySelectorAll('[data-store-search-open]');
    let active = -1;
    let options = [];
    let timer = null;
    let controller = null;
    let generation = 0;
    let returnFocus = null;

    function select(index) {
        active = index;
        options.forEach(function (option, position) {
            option.setAttribute('aria-selected', position === active ? 'true' : 'false');
        });
        if (active >= 0 && options[active]) {
            input.setAttribute('aria-activedescendant', options[active].id);
            options[active].scrollIntoView({ block: 'nearest' });
        } else {
            input.removeAttribute('aria-activedescendant');
        }
    }

    function resetResults() {
        select(-1);
        options = [];
        list.replaceChildren();
        input.setAttribute('aria-expanded', 'false');
        correction.hidden = true;
        shop.hidden = true;
    }

    function appendParts(element, parts, fallback) {
        (Array.isArray(parts) ? parts : [{ text: fallback, match: false }]).forEach(function (part) {
            if (part.match) {
                const mark = document.createElement('mark');
                mark.textContent = part.text;
                element.appendChild(mark);
            } else {
                element.appendChild(document.createTextNode(part.text));
            }
        });
    }

    function render(data) {
        resetResults();
        const results = Array.isArray(data.results) ? data.results : [];
        results.forEach(function (result, index) {
            const item = document.createElement('li');
            item.setAttribute('role', 'presentation');
            const link = document.createElement('a');
            link.className = 'store-search-option';
            link.id = 'store-search-option-' + index;
            link.href = result.url;
            link.tabIndex = -1;
            link.setAttribute('role', 'option');
            link.setAttribute('aria-selected', 'false');
            const category = document.createElement('span');
            category.className = 'store-search-category';
            category.textContent = result.category;
            const title = document.createElement('strong');
            appendParts(title, result.title_parts, result.title);
            const summary = document.createElement('span');
            summary.className = 'store-search-summary';
            appendParts(summary, result.description_parts, result.description);
            link.append(category, title, summary);
            link.addEventListener('mouseenter', function () { select(index); });
            item.appendChild(link);
            list.appendChild(item);
            options.push(link);
        });
        input.setAttribute('aria-expanded', results.length ? 'true' : 'false');
        status.textContent = data.error || (data.is_initial ? 'Popular club pages' : results.length
            ? data.total + ' matching page' + (data.total === 1 ? '' : 's') + (data.total > results.length ? '. Press Enter to see all results.' : '.')
            : 'No club pages found. Try another topic' + (data.shop_search_url ? ' or search the shop below.' : '.'));
        if (data.did_you_mean) {
            correction.textContent = 'Did you mean “' + data.did_you_mean + '”?';
            correction.dataset.searchQuery = data.did_you_mean;
            correction.hidden = false;
        }
        if (data.shop_search_url) {
            shop.href = data.shop_search_url;
            shop.hidden = false;
        }
    }

    async function fetchResults(version) {
        controller = new AbortController();
        list.setAttribute('aria-busy', 'true');
        status.textContent = 'Searching…';
        try {
            const url = new URL(input.dataset.suggestionsUrl, window.location.href);
            url.searchParams.set('q', input.value);
            const response = await fetch(url, { signal: controller.signal, credentials: 'same-origin', headers: { Accept: 'application/json' } });
            if (!response.ok) throw new Error('Search unavailable');
            const data = await response.json();
            if (version === generation && dialog.open) render(data);
        } catch (error) {
            if (error.name !== 'AbortError' && version === generation && dialog.open) {
                resetResults();
                status.textContent = 'Suggestions could not load. Press Enter to open the search results page.';
            }
        } finally {
            if (version === generation) list.setAttribute('aria-busy', 'false');
        }
    }

    function schedule(immediate) {
        generation += 1;
        if (controller) controller.abort();
        window.clearTimeout(timer);
        resetResults();
        list.setAttribute('aria-busy', 'false');
        clear.hidden = !input.value;
        if (input.value.trim() && Array.from(input.value.trim()).length < 2) {
            status.textContent = 'Type at least 2 characters to search.';
            return;
        }
        const version = generation;
        timer = window.setTimeout(function () { fetchResults(version); }, immediate ? 0 : 180);
    }

    function open(trigger) {
        if (dialog.open || document.querySelector('dialog[open]')) return;
        returnFocus = trigger;
        dialog.showModal();
        document.documentElement.classList.add('store-search-open');
        input.focus();
        schedule(true);
    }

    triggers.forEach(function (trigger) {
        trigger.addEventListener('click', function (event) {
            event.preventDefault();
            open(trigger);
        });
    });
    input.addEventListener('input', function () { schedule(false); });
    input.addEventListener('keydown', function (event) {
        if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && options.length) {
            event.preventDefault();
            const next = event.key === 'ArrowDown' ? (active + 1) % options.length : (active <= 0 ? options.length - 1 : active - 1);
            select(next);
        } else if (event.key === 'Enter' && active >= 0 && options[active]) {
            event.preventDefault();
            window.location.assign(options[active].href);
        }
    });
    clear.addEventListener('click', function () { input.value = ''; input.focus(); schedule(true); });
    dialog.querySelector('[data-store-search-close]').addEventListener('click', function () { dialog.close(); });
    dialog.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            event.preventDefault();
            dialog.close();
        }
    });
    dialog.addEventListener('click', function (event) {
        const topic = event.target.closest('[data-search-query]');
        if (topic) { input.value = topic.dataset.searchQuery; input.focus(); schedule(true); return; }
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    dialog.addEventListener('close', function () {
        generation += 1;
        window.clearTimeout(timer);
        if (controller) controller.abort();
        document.documentElement.classList.remove('store-search-open');
        input.setAttribute('aria-expanded', 'false');
        input.removeAttribute('aria-activedescendant');
        if (returnFocus) returnFocus.focus();
    });
    document.addEventListener('keydown', function (event) {
        const editing = event.target && event.target.closest && event.target.closest('input, textarea, select, [contenteditable]');
        if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !editing && !dialog.open && !document.querySelector('dialog[open]')) {
            event.preventDefault();
            if (triggers.length) open(triggers[0]);
        }
    });
})();

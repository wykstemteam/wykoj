// Search bar
$(() => {
    if ($(".navbar-search").length) {
        $(".search-results").width($(".search").width());

        $(".search-query").on("keydown", e => {
            // TODO: Add behavior on enter
            if (e.keyCode == 13) {
                e.preventDefault();
            }
        });

        $(".search-query").on("input", e => {
            const query = $(e.target).val();
            const searchResultList = $(".search-result-list");
            searchResultList.empty();
            if (query.length < 3 || query.length > 50) {
                return;
            }
            $.getJSON("/search?query=" + encodeURIComponent(query), (data) => {
                if ($(e.target).val() != query) {  // Check if query changed
                    return;
                }
                let elements = [];
                data["tasks"].forEach(task => {
                    elements.push(`<a href="/task/${task.task_id}" class="search-result-link">
                        <li class="search-result">${task.task_id} - ${task.title}</li>
                    </a>`);
                });
                data["users"].forEach(user => {
                    elements.push(`<a href="/user/${user.username}" class="search-result-link">
                        <li class="search-result">${user.username} - ${user.name}</li>
                    </a>`);
                });
                searchResultList.html(
                    elements.join("") || '<li class="search-result no-hover-fx">No results</li>'
                );
            });
        })
    }
});

// omitted headers

int contestant(int); // function contestant should implement

namespace { // Anonymous namespace so other cpp files cannot call
    // Declare your variables here
    int total_query_count = 0;

    double get_score(int N) {
        return 100.0 - exp(total_query_count);
    } 

    int query_func_impl(int M) {
        total_query_count += 1;
        // ...
    }
};

int query_func(int M) {
    return query_func_impl(M);
}

string grader() {
    int N, jury_ans; // read from input files
    cin >> N >> jury_ans;
    
    int contestant_ans = contestant(N);

    if (contestant_ans == jury_ans) {
        double score = get_score(N);
        if (score > 100.0) {
            return "AC\n";
        } else {
            return "PS " + to_string(score);
        }
    } else {
        return "WA\n";
    }
}
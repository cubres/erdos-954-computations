#include "../src/audit_histogram.hpp"
#include <iostream>

using U = uint64_t;

void check(const std::vector<U>& a, U low, U high) {
    // Deliberately include unused trailing storage and nonzero old contents.
    std::vector<uint32_t> actual(high - low + 3, 37);
    std::vector<uint32_t> expected(high - low, 0);
    for (size_t i = 0; i < a.size(); ++i)
        for (size_t j = i; j < a.size(); ++j)
            if (a[i] + a[j] >= low && a[i] + a[j] < high)
                ++expected[a[i] + a[j] - low];
    erdos954::positive_pair_histogram(a, low, high, actual);
    if (!std::equal(expected.begin(), expected.end(), actual.begin()))
        throw std::runtime_error("histogram differs from direct pair enumeration");
    for (size_t i = expected.size(); i < actual.size(); ++i)
        if (actual[i] != 37) throw std::runtime_error("wrote beyond the interval");
}

int main() {
    try {
        U checks = 0;
        for (unsigned mask = 0; mask < (1U << 9); ++mask) {
            std::vector<U> a;
            for (unsigned bit = 0; bit < 9; ++bit)
                if (mask & (1U << bit)) a.push_back(bit + 1);
            for (U low = 1; low <= 20; ++low)
                for (U high = low + 1; high <= 21; ++high) {
                    check(a, low, high);
                    ++checks;
                }
        }
        const U large = 1000000000000000ULL;
        const std::vector<U> a{1, 3, large / 2, large - 2, large - 1, large};
        for (U sum : {U(2), U(4), U(6), large / 2 + 1, large, 2 * large})
            for (U low = sum > 3 ? sum - 3 : 1; low <= sum + 2; ++low)
                for (U width : {U(1), U(2), U(7)}) {
                    check(a, low, low + width);
                    ++checks;
                }
        for (auto interval : {std::pair<U,U>{5,5}, {6,5}, {1,5}}) {
            std::vector<uint32_t> small(2);
            bool rejected = false;
            try {
                erdos954::positive_pair_histogram(a, interval.first, interval.second, small);
            } catch (const std::runtime_error&) { rejected = true; }
            if (!rejected) throw std::runtime_error("invalid interval accepted");
        }
        std::cout << "PASS histogram comparisons=" << checks << "\n";
    } catch (const std::exception& e) {
        std::cerr << "FAIL " << e.what() << "\n";
        return 1;
    }
}

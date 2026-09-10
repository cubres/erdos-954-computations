#pragma once

#include <algorithm>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace erdos954 {

// Reconstruct positive unordered pairs in [low, high), including diagonals.
// The caller supplies strictly increasing positive terms, each at most 10^15.
// Both partner thresholds decrease as the first summand increases. Rebuild
// their pointers from the final list for every block; no generator state is used.
inline void positive_pair_histogram(const std::vector<uint64_t>& a,
                                    uint64_t low, uint64_t high,
                                    std::vector<uint32_t>& hist) {
    if (high <= low || high - low > hist.size())
        throw std::runtime_error("invalid histogram interval");
    std::fill(hist.begin(), hist.begin() + (high - low), 0);
    if (a.empty() || a.front() >= high) return;
    // One initial search avoids traversing the unused tail of a long prefix.
    size_t upper = std::lower_bound(a.begin(), a.end(), high - a.front()) - a.begin();
    size_t lower = upper;
    for (size_t i = 0; i < upper; ++i) {
        while (upper > i && a[i] + a[upper - 1] >= high) --upper;
        if (upper <= i) break;
        while (lower > i && a[i] + a[lower - 1] >= low) --lower;
        lower = std::max(lower, i);
        for (size_t j = lower; j < upper; ++j) {
            auto& cell = hist[a[i] + a[j] - low];
            if (cell == std::numeric_limits<uint32_t>::max())
                throw std::runtime_error("histogram overflow");
            ++cell;
        }
    }
}

} // namespace erdos954

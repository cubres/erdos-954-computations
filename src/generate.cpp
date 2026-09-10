// Exact, resumable-by-prefix generator for corrected Erdos problem 954.
// The bulk step uses only E(x)>=0 and the fact that E falls by at most 1 per step.
#include <algorithm>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

using U = uint64_t;
static volatile std::sig_atomic_t stop_requested = 0;
static void stop(int) { stop_requested = 1; }
static U number(const std::string& s) {
    if (s.empty() || s.find_first_not_of("0123456789") != std::string::npos)
        throw std::runtime_error("expected an unsigned decimal integer");
    return std::stoull(s);
}
static std::vector<U> read_terms(const std::string& path, U limit) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open seed CSV");
    std::string line;
    if (!std::getline(in, line) || line != "index,value")
        throw std::runtime_error("expected CSV header index,value");
    std::vector<U> a;
    while (std::getline(in, line)) {
        if (in.eof()) throw std::runtime_error("seed ends with an incomplete line");
        const auto comma = line.find(',');
        if (comma == std::string::npos || number(line.substr(0, comma)) != a.size()+1)
            throw std::runtime_error("invalid seed index");
        U x = number(line.substr(comma+1));
        if (x > limit || (!a.empty() && x <= a.back()) || (a.empty() && x != 1))
            throw std::runtime_error("invalid seed value");
        a.push_back(x);
    }
    if (!in.eof() || a.empty()) throw std::runtime_error("unreadable or empty seed");
    return a;
}
static U cumulative(const std::vector<U>& a, U x) {
    size_t j = std::upper_bound(a.begin(), a.end(), x)-a.begin();
    U result = j;
    for (size_t i=0; i<j; ++i) {
        while (j>i && a[i]+a[j-1]>x) --j;
        if (j<=i) break;
        if (result > std::numeric_limits<U>::max()-(j-i))
            throw std::runtime_error("cumulative count overflow");
        result += j-i;
    }
    return result;
}

int main(int argc, char** argv) {
    try {
        const bool cumulative_jumps=argc>1 && std::string(argv[argc-1])=="--jump";
        if (cumulative_jumps) --argc;
        if (argc<3 || argc>6) {
            std::cerr << "usage: generate LIMIT OUTPUT_PREFIX [BLOCK [SEED_CSV|- [WORKERS]]] [--jump]\n";
            return 2;
        }
        const U limit=number(argv[1]), block=argc>3 ? number(argv[3]) : 33554432;
        const U workers=argc>5 ? number(argv[5]) : 1;
        // Bound every sum of two term values and every block endpoint in uint64.
        if (!limit || limit>1000000000000000ULL || !block || block>1073741824ULL)
            throw std::runtime_error("require 1<=LIMIT<=10^15 and 1<=BLOCK<=2^30");
        if (!workers || workers>64) throw std::runtime_error("workers must be 1..64");
        const std::string prefix=argv[2];
        const std::string csv=prefix+"_terms.csv", summary=prefix+"_summary.json";
        if (std::filesystem::exists(csv) || std::filesystem::exists(summary))
            throw std::runtime_error("output already exists; use a new prefix");
        auto a=argc>4 && std::string(argv[4])!="-" ? read_terms(argv[4], limit) : std::vector<U>{};
        const U seed_last=a.empty()?0:a.back(), seed_terms=a.size();
        // This is an endpoint sanity check, NOT a full audit of the seed.
        if (seed_last && (cumulative(a,seed_last)!=seed_last ||
                          cumulative(a,seed_last-1)!=seed_last-1))
            throw std::runtime_error("seed endpoint is not a contact");
        std::ofstream terms;
        terms.exceptions(std::ios::badbit | std::ios::failbit);
        terms.open(csv);
        terms << "index,value\n";
        for (size_t i=0; i<a.size(); ++i) terms << i+1 << ',' << a[i] << '\n';
        std::vector<uint8_t> hist(std::min(block,limit));
        U error=0, processed=seed_last, bulk_positions=0;
        U cumulative_jump_positions=0, cumulative_jump_queries=0, histogram_blocks=0;
        const auto start=std::chrono::steady_clock::now();
        auto last_report=start;
        const auto report=[&](const char* status) {
            terms.flush();
            const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
            const std::string temp=summary+".tmp";
            std::ofstream out;
            out.exceptions(std::ios::badbit | std::ios::failbit);
            out.open(temp);
            out << "{\"status\":\"" << status << "\",\"target_limit\":" << limit
                << ",\"processed_through\":" << processed << ",\"terms\":" << a.size()
                << ",\"last_term\":" << (a.empty()?0:a.back()) << ",\"E\":" << error
                << ",\"seed_last\":" << seed_last << ",\"seed_terms\":" << seed_terms
                << ",\"block\":" << block << ",\"bulk_positions\":" << bulk_positions
                << ",\"cumulative_jumps\":" << (cumulative_jumps?"true":"false")
                << ",\"cumulative_jump_positions\":" << cumulative_jump_positions
                << ",\"cumulative_jump_queries\":" << cumulative_jump_queries
                << ",\"histogram_blocks\":" << histogram_blocks
                << ",\"workers\":" << workers
                << ",\"seconds\":" << seconds << ",\"independently_audited\":false}\n";
            out.close();
            std::filesystem::rename(temp,summary);
            std::cout << "x=" << processed << " A=" << a.size() << " E=" << error
                      << " seconds=" << seconds << " status=" << status << '\n' << std::flush;
        };
        std::signal(SIGINT,stop);
        std::signal(SIGTERM,stop);
        report("RUNNING");
        for (U left=seed_last+1; left<=limit && !stop_requested;) {
            if (cumulative_jumps && error>=std::max<U>(1024,2*a.size())) {
                // No insertion is possible in the next min(E, remaining)
                // positions. Recount the endpoint from the unchanged prefix.
                const U span=std::min(error,limit-processed);
                const U target=processed+span;
                const U count=cumulative(a,target);
                if (count<target) throw std::runtime_error("negative jump endpoint error");
                error=count-target; processed=target; left=processed+1;
                cumulative_jump_positions+=span; ++cumulative_jump_queries;
                const auto now=std::chrono::steady_clock::now();
                if (std::chrono::duration<double>(now-last_report).count()>=30) {
                    report("RUNNING"); last_report=now;
                }
                continue;
            }
            ++histogram_blocks;
            const U right=std::min(limit+1,left+block), len=right-left;
            std::fill(hist.begin(),hist.begin()+len,0);
            auto inc=[&](U idx) {
                auto& cell=hist[idx];
                if (cell==255) throw std::runtime_error("8-bit arrival histogram overflow; widen histogram and rerun");
                ++cell;
            };
            const size_t old=a.size();
            const auto fill_range=[&](U low,U high) {
                if (low==high) return;
                size_t lo=old,hi=old;
                for (size_t i=0; i<old && 2*a[i]<high; ++i) {
                    while (lo>0 && a[lo-1]+a[i]>=low) --lo;
                    while (hi>0 && a[hi-1]+a[i]>=high) --hi;
                    for (size_t j=std::max(i,lo); j<hi; ++j) inc(a[i]+a[j]-left);
                }
            };
            if (workers==1 || old<1000 || len<65536) {
                fill_range(left,right);
            } else {
                std::vector<std::thread> threads;
                std::mutex failure_mutex;
                std::exception_ptr failure;
                try {
                    for (U w=0; w<workers; ++w) threads.emplace_back([&,w] {
                        try {
                            // Disjoint histogram cells; a is immutable until join.
                            fill_range(left+len*w/workers,left+len*(w+1)/workers);
                        } catch (...) {
                            std::lock_guard<std::mutex> lock(failure_mutex);
                            if (!failure) failure=std::current_exception();
                        }
                    });
                } catch (...) {
                    for (auto& t:threads) t.join();
                    throw;
                }
                for (auto& t:threads) t.join();
                if (failure) std::rethrow_exception(failure);
            }
            for (U x=left; x<right;) {
                if (error>=1024) {
                    const U span=std::min(error,right-x);
                    U arrivals=0;
                    // No insertion in these span positions: before their last
                    // position the error is still >=1, even if every arrival is 0.
                    for (U k=x-left; k<x-left+span; ++k) arrivals+=hist[k];
                    if (error-span>std::numeric_limits<U>::max()-arrivals)
                        throw std::runtime_error("error overflow");
                    error=error-span+arrivals;
                    x+=span; bulk_positions+=span;
                } else {
                    const U r=hist[x-left];
                    if (!error && !r) {
                        a.push_back(x);
                        terms << a.size() << ',' << x << '\n';
                        for (U b:a) { if (x+b>=right) break; inc(x+b-left); }
                    } else {
                        error=error+r-1;
                    }
                    ++x;
                }
            }
            processed=right-1; left=right;
            const auto now=std::chrono::steady_clock::now();
            if (std::chrono::duration<double>(now-last_report).count()>=30) {
                report("RUNNING"); last_report=now;
            }
        }
        if (cumulative(a,processed)!=processed+error)
            throw std::runtime_error("independent endpoint recount mismatch");
        report(processed==limit?"COMPLETE":"STOPPED");
        terms.close();
        return processed==limit?0:3;
    } catch (const std::exception& e) {
        std::cerr << "FAIL " << e.what() << '\n';
        return 1;
    }
}

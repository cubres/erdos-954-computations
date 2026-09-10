// Independent interval audit of a supplied final term list.
// Strict endpoint enclosures certify positive-error regions below an exact
// witnessed maximum; all remaining intervals are inspected with histograms.
// The optional decisions-only mode omits maximum checks and can audit a suffix
// conditional on a separately verified, matching prefix.
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include "audit_histogram.hpp"
using U = uint64_t;

U number(const std::string& s) {
    if (s.empty() || s.find_first_not_of("0123456789") != std::string::npos)
        throw std::runtime_error("expected unsigned decimal integer");
    return std::stoull(s);
}

U cumulative(const std::vector<U>& a, U x) {
    size_t j=std::upper_bound(a.begin(),a.end(),x)-a.begin();
    U total=j;
    for (size_t i=0; i<j; ++i) {
        while (j>i && a[i]+a[j-1]>x) --j;
        if (j<=i) break;
        if (total>std::numeric_limits<U>::max()-(j-i))
            throw std::runtime_error("cumulative count overflow");
        total+=j-i;
    }
    return total;
}

struct Totals {
    U terms=0, zeros=0, maximum=0, first=0, last=0, final_count=0;
    U scanned=0, certified=0, pruned=0, leaves=0, queries=0;
};

int main(int argc, char** argv) {
    try {
        if (argc<4) {
            std::cerr<<"usage: audit_intervals TERM_CSV LIMIT OUTPUT_JSON [WORKERS] [LEAF] [CHUNK]"
                     <<" [--decisions-only] [--start N]\n";
            return 2;
        }
        const U limit=number(argv[2]);
        U options[]={3,1048576,1073741824};
        int arg=4;
        for (unsigned pos=0;pos<3 && arg<argc && std::string(argv[arg]).rfind("--",0)!=0;++pos)
            options[pos]=number(argv[arg++]);
        bool decisions_only=false, has_start=false;
        U start_exclusive=0;
        while (arg<argc) {
            const std::string option=argv[arg++];
            if (option=="--decisions-only" && !decisions_only) decisions_only=true;
            else if (option=="--start" && !has_start && arg<argc) {
                has_start=true; start_exclusive=number(argv[arg++]);
            } else throw std::runtime_error("unknown, duplicate, or incomplete audit option");
        }
        const U worker_arg=options[0], leaf=options[1], chunk=options[2];
        if (!limit || limit>1000000000000000ULL || !worker_arg || worker_arg>256 ||
            !leaf || leaf>1073741824ULL || !chunk || chunk>1000000000000000ULL ||
            start_exclusive>=limit || (has_start && !decisions_only))
            throw std::runtime_error("invalid limit, worker count, leaf size, chunk size, or start option");
        const unsigned workers=static_cast<unsigned>(worker_arg);
        if (std::filesystem::exists(argv[3])) throw std::runtime_error("output already exists");
        std::ifstream in(argv[1]);
        if (!in) throw std::runtime_error("missing term list");
        std::string line;
        if (!std::getline(in,line) || line!="index,value") throw std::runtime_error("invalid CSV header");
        std::vector<U> a;
        while (std::getline(in,line)) {
            if (in.eof()) throw std::runtime_error("incomplete CSV line");
            auto comma=line.find(',');
            if (comma==std::string::npos || number(line.substr(0,comma))!=a.size()+1)
                throw std::runtime_error("invalid CSV index");
            a.push_back(number(line.substr(comma+1)));
        }
        if (!in.eof()) throw std::runtime_error("CSV read failure");
        if (a.empty() || a.front()!=1 || a.back()>limit) throw std::runtime_error("invalid term endpoints");
        for (size_t i=1;i<a.size();++i)
            if (a[i]<=a[i-1]) throw std::runtime_error("terms not strictly increasing");
        const U range_length=limit-start_exclusive;
        const size_t prefix_terms=std::upper_bound(a.begin(),a.end(),start_exclusive)-a.begin();
        const auto start=std::chrono::steady_clock::now();
        std::atomic<U> witnessed_maximum{0};
        auto observe=[&](U e) {
            U old=witnessed_maximum.load(std::memory_order_relaxed);
            while (old<e && !witnessed_maximum.compare_exchange_weak(old,e,std::memory_order_relaxed)) {}
        };
        // These exact values are lower bounds for the maximum. They are never
        // used to count maximizing positions; every final maximizer is scanned.
        const U samples=decisions_only?0:std::min<U>(64,limit);
        for (U s=1;s<=samples;++s) {
            const U x=(limit/samples)*s+((limit%samples)*s)/samples;
            const U count=cumulative(a,x);
            if (count<x) throw std::runtime_error("negative error at sample "+std::to_string(x));
            observe(count-x);
        }
        const U chunks=(range_length-1)/chunk+1;
        std::atomic<U> next{0}, completed{0};
        std::atomic<bool> failed{false};
        std::mutex message_mutex;
        std::string failure;
        std::vector<Totals> totals(workers);
        std::vector<std::thread> threads;
        for (unsigned w=0;w<workers;++w) threads.emplace_back([&,w] {
            try {
                auto& result=totals[w];
                std::vector<uint32_t> hist(std::min({leaf,chunk,limit}));
                auto query=[&](U x) { ++result.queries; return cumulative(a,x); };
                std::function<void(U,U,U,U)> visit;
                visit=[&](U low,U high,U left,U right) {
                    if (failed.load(std::memory_order_relaxed)) return;
                    if (left<low-1 || right<high)
                        throw std::runtime_error("negative error at interval endpoint");
                    // For low<=x<=high, left-high <= E(x) <= right-low.
                    // A decision-only audit needs the strict lower enclosure,
                    // but makes no claim about the maximum in skipped regions.
                    if (left>high && (decisions_only ||
                            right-low<witnessed_maximum.load(std::memory_order_relaxed))) {
                        auto term=std::lower_bound(a.begin(),a.end(),low);
                        if (term!=a.end() && *term<=high)
                            throw std::runtime_error("positive-error contact in certified interval");
                        result.certified+=high-low+1; ++result.pruned;
                        if (high==limit) result.final_count=right;
                        return;
                    }
                    if (high-low+1>leaf) {
                        const U middle=low+(high-low)/2;
                        const U midcount=query(middle);
                        visit(low,middle,left,midcount);
                        visit(middle+1,high,midcount,right);
                        return;
                    }
                    erdos954::positive_pair_histogram(a,low,high+1,hist);
                    U count=left, previous=left-(low-1);
                    size_t pos=std::lower_bound(a.begin(),a.end(),low)-a.begin();
                    for (U x=low;x<=high;++x) {
                        const U arrival=hist[x-low];
                        const bool term=pos<a.size() && a[pos]==x;
                        if (count>std::numeric_limits<U>::max()-arrival-U(term))
                            throw std::runtime_error("cumulative count overflow");
                        count+=arrival;
                        if (term) { ++count; ++pos; ++result.terms; }
                        if (count<x) throw std::runtime_error("negative error at "+std::to_string(x));
                        const U error=count-x;
                        if (term && (error || previous || arrival))
                            throw std::runtime_error("invalid contact at "+std::to_string(x));
                        if (!term && previous==0 && arrival==0)
                            throw std::runtime_error("missed insertion at "+std::to_string(x));
                        if (error==0) ++result.zeros;
                        if (error>result.maximum) {
                            result.maximum=error; result.first=result.last=x;
                        } else if (error==result.maximum) {
                            if (!result.first) result.first=x;
                            result.last=std::max(result.last,x);
                        }
                        previous=error;
                    }
                    if (count!=right) throw std::runtime_error("leaf endpoint count mismatch");
                    observe(result.maximum);
                    result.scanned+=high-low+1; ++result.leaves;
                    if (high==limit) result.final_count=count;
                };
                while (!failed.load()) {
                    const U k=next.fetch_add(1);
                    if (k>=chunks) break;
                    const U low=start_exclusive+1+k*chunk, high=std::min(limit,low+chunk-1);
                    const U left=query(low-1), right=query(high);
                    visit(low,high,left,right);
                    const U done=completed.fetch_add(1)+1;
                    if (done%std::max<U>(1,chunks/10)==0 || done==chunks) {
                        std::lock_guard<std::mutex> lock(message_mutex);
                        std::cout<<"chunks="<<done<<"/"<<chunks<<"\n"<<std::flush;
                    }
                }
            } catch (const std::exception& e) {
                std::lock_guard<std::mutex> lock(message_mutex);
                if (failure.empty()) failure=e.what();
                failed.store(true);
            }
        });
        for (auto& t:threads) t.join();
        if (failed.load()) throw std::runtime_error(failure);
        Totals all;
        for (const auto& t:totals) {
            all.terms+=t.terms; all.zeros+=t.zeros; all.final_count+=t.final_count;
            all.scanned+=t.scanned; all.certified+=t.certified; all.pruned+=t.pruned;
            all.leaves+=t.leaves; all.queries+=t.queries;
            if (t.maximum>all.maximum) {
                all.maximum=t.maximum; all.first=t.first; all.last=t.last;
            } else if (t.maximum==all.maximum && t.first) {
                if (!all.first || t.first<all.first) all.first=t.first;
                all.last=std::max(all.last,t.last);
            }
        }
        if (all.terms!=a.size()-prefix_terms || completed.load()!=chunks ||
            all.scanned+all.certified!=range_length ||
            (!decisions_only && (all.maximum!=witnessed_maximum.load() || !all.first)))
            throw std::runtime_error("incomplete coverage or maximum accounting");
        const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::ofstream out(argv[3]);
        if (!out) throw std::runtime_error("cannot write output");
        out.exceptions(std::ios::badbit|std::ios::failbit);
        out<<"{\"status\":\"PASS\",\"limit\":"<<limit<<",\"terms\":"<<a.size()
           <<",\"R_limit\":"<<all.final_count<<",\"E_limit\":"<<all.final_count-limit
           <<",\"start_exclusive\":"<<start_exclusive
           <<",\"prefix_assumed_valid_through\":"<<start_exclusive
           <<",\"range_terms_checked\":"<<all.terms
           <<",\"maximum_evaluated\":"<<(decisions_only?"false":"true");
        if (!decisions_only)
            out<<",\"maximum_error\":"<<all.maximum<<",\"first_maximizer\":"<<all.first
               <<",\"last_maximizer\":"<<all.last;
        if (start_exclusive==0) out<<",\"zero_error_positions\":"<<all.zeros;
        out<<",\"range_zero_error_positions\":"<<all.zeros
           <<",\"all_contacts_checked\":"<<(start_exclusive==0?"true":"false")
           <<",\"all_greedy_decisions_checked\":"<<(start_exclusive==0?"true":"false")
           <<",\"all_range_contacts_checked\":true,\"all_range_greedy_decisions_checked\":true"
           <<",\"method\":\""<<(decisions_only?"greedy_decision_enclosures_and_histograms":
                                                    "endpoint_enclosures_and_histograms")<<"\""
           <<",\"positions_scanned\":"<<all.scanned
           <<",\"positions_certified_by_enclosure\":"<<all.certified<<",\"pruned_intervals\":"<<all.pruned
           <<",\"histogram_leaves\":"<<all.leaves<<",\"interval_count_queries\":"<<all.queries
           <<",\"sample_queries\":"<<samples<<",\"workers\":"<<workers<<",\"leaf\":"<<leaf
           <<",\"chunk\":"<<chunk<<",\"seconds\":"<<seconds<<"}\n";
        out.close();
        std::cout<<"PASS start_exclusive="<<start_exclusive<<" limit="<<limit;
        if (!decisions_only) std::cout<<" maximum="<<all.maximum;
        std::cout<<" certified="<<all.certified
                 <<" scanned="<<all.scanned<<" seconds="<<seconds<<"\n";
    } catch (const std::exception& e) {
        std::cerr<<"FAIL "<<e.what()<<"\n"; return 1;
    }
}

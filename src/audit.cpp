// Independent final-list audit. Each worker reconstructs a block from scratch,
// including its initial cumulative count; no online generator state is reused.
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <filesystem>
#include <iostream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
using U = uint64_t;

U number(const std::string& s) {
    if(s.empty() || s.find_first_not_of("0123456789")!=std::string::npos)
        throw std::runtime_error("expected unsigned decimal integer");
    return std::stoull(s);
}

struct Totals {
    U terms=0, zeros=0, maximum=0, first=0, last=0, final_count=0;
};

U cumulative(const std::vector<U>& a, U x) {
    size_t j=std::upper_bound(a.begin(),a.end(),x)-a.begin();
    U total=j;
    for(size_t i=0;i<j;++i) {
        while(j>i && a[i]+a[j-1]>x) --j;
        if(j<=i) break;
        total+=j-i;
    }
    return total;
}

int main(int argc,char** argv) {
    try {
        if(argc<4 || argc>6) {
            std::cerr << "usage: verify_offline_parallel TERM_CSV LIMIT OUTPUT_JSON [WORKERS] [BLOCK]\n";
            return 2;
        }
        const U limit=number(argv[2]);
        const U worker_arg=argc>4?number(argv[4]):3;
        if(!worker_arg || worker_arg>256) throw std::runtime_error("workers must be 1..256");
        const unsigned workers=static_cast<unsigned>(worker_arg);
        const U block=argc>5?number(argv[5]):8388608;
        if(!limit || limit>1000000000000000ULL || !block || block>1073741824ULL)
            throw std::runtime_error("require 1<=LIMIT<=10^15 and 1<=BLOCK<=2^30");
        if(std::filesystem::exists(argv[3])) throw std::runtime_error("output already exists");
        std::ifstream in(argv[1]);
        if(!in) throw std::runtime_error("missing term list");
        std::string line;
        if(!std::getline(in,line) || line!="index,value") throw std::runtime_error("invalid CSV header");
        std::vector<U> a;
        while(std::getline(in,line)) {
            if(in.eof()) throw std::runtime_error("incomplete CSV line");
            auto comma=line.find(',');
            if(comma==std::string::npos || number(line.substr(0,comma))!=a.size()+1)
                throw std::runtime_error("invalid CSV index");
            a.push_back(number(line.substr(comma+1)));
        }
        if(!in.eof()) throw std::runtime_error("CSV read failure");
        if(a.empty() || a[0]!=1 || a.back()>limit) throw std::runtime_error("invalid term endpoints");
        for(size_t i=1;i<a.size();++i)
            if(a[i]<=a[i-1]) throw std::runtime_error("terms not strictly increasing");
        const auto start=std::chrono::steady_clock::now();
        const U blocks=(limit-1)/block+1;
        std::atomic<U> next{0}, completed{0};
        std::atomic<bool> failed{false};
        std::mutex message_mutex;
        std::string failure;
        std::vector<Totals> totals(workers);
        std::vector<std::thread> threads;
        for(unsigned w=0;w<workers;++w) threads.emplace_back([&,w] {
            try {
                std::vector<uint32_t> hist(std::min(block,limit));
                auto& result=totals[w];
                while(!failed.load()) {
                    const U k=next.fetch_add(1);
                    if(k>=blocks) break;
                    const U low=1+k*block, high=std::min(limit+1,low+block);
                    std::fill(hist.begin(),hist.end(),0);
                    for(size_t i=0;i<a.size() && 2*a[i]<high;++i) {
                        U lower=low>a[i]?low-a[i]:0, upper=high-a[i];
                        auto begin=std::lower_bound(a.begin()+i,a.end(),lower);
                        auto end=std::lower_bound(begin,a.end(),upper);
                        for(auto it=begin;it!=end;++it) {
                            auto& cell=hist[a[i]+*it-low];
                            if(cell==std::numeric_limits<uint32_t>::max())
                                throw std::runtime_error("histogram overflow");
                            ++cell;
                        }
                    }
                    U count=cumulative(a,low-1);
                    if(count<low-1) throw std::runtime_error("negative initial error");
                    U previous=count-(low-1);
                    size_t pos=std::lower_bound(a.begin(),a.end(),low)-a.begin();
                    for(U x=low;x<high;++x) {
                        const U arrival=hist[x-low];
                        const bool term=pos<a.size() && a[pos]==x;
                        count+=arrival;
                        if(term) {++count; ++pos; ++result.terms;}
                        if(count<x) throw std::runtime_error("negative error at "+std::to_string(x));
                        const U error=count-x;
                        if(term && (error || previous || arrival))
                            throw std::runtime_error("invalid contact at "+std::to_string(x));
                        if(!term && previous==0 && arrival==0)
                            throw std::runtime_error("missed insertion at "+std::to_string(x));
                        if(error==0) ++result.zeros;
                        if(error>result.maximum) {
                            result.maximum=error;
                            result.first=result.last=x;
                        } else if(error==result.maximum) {
                            if(!result.first || x<result.first) result.first=x;
                            result.last=std::max(result.last,x);
                        }
                        previous=error;
                    }
                    if(high==limit+1) result.final_count=count;
                    U done=completed.fetch_add(1)+1;
                    if(done%std::max<U>(1,blocks/10)==0 || done==blocks) {
                        std::lock_guard<std::mutex> lock(message_mutex);
                        std::cout << "blocks=" << done << "/" << blocks << "\n" << std::flush;
                    }
                }
            } catch(const std::exception& e) {
                std::lock_guard<std::mutex> lock(message_mutex);
                if(failure.empty()) failure=e.what();
                failed.store(true);
            }
        });
        for(auto& t:threads) t.join();
        if(failed.load()) throw std::runtime_error(failure);
        Totals all;
        for(const auto& t:totals) {
            all.terms+=t.terms; all.zeros+=t.zeros;
            all.final_count+=t.final_count;
            if(t.maximum>all.maximum) {
                all.maximum=t.maximum; all.first=t.first; all.last=t.last;
            } else if(t.maximum==all.maximum && t.first) {
                if(!all.first || t.first<all.first) all.first=t.first;
                all.last=std::max(all.last,t.last);
            }
        }
        if(all.terms!=a.size() || completed.load()!=blocks)
            throw std::runtime_error("incomplete coverage");
        const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::ofstream out(argv[3]);
        if(!out) throw std::runtime_error("cannot write output");
        out.exceptions(std::ios::badbit | std::ios::failbit);
        out << "{\"status\":\"PASS\",\"limit\":" << limit
            << ",\"terms\":" << all.terms << ",\"R_limit\":" << all.final_count
            << ",\"E_limit\":" << all.final_count-limit
            << ",\"maximum_error\":" << all.maximum
            << ",\"first_maximizer\":" << all.first << ",\"last_maximizer\":" << all.last
            << ",\"zero_error_positions\":" << all.zeros
            << ",\"all_contacts_checked\":true,\"all_greedy_decisions_checked\":true"
            << ",\"blocks\":" << blocks << ",\"workers\":" << workers
            << ",\"block\":" << block << ",\"seconds\":" << seconds << "}\n";
        out.close();
        std::cout << "PASS limit=" << limit << " maximum=" << all.maximum
                  << " seconds=" << seconds << "\n";
    } catch(const std::exception& e) {
        std::cerr << "FAIL " << e.what() << "\n";
        return 1;
    }
}

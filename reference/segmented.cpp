#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
using U=uint64_t;
struct Check {U x,n,e,m,peak,gap;};
U count_pairs(const std::vector<U>& a,U x){
    // Positive pairs followed by the zero-pair contribution.
    U total=std::upper_bound(a.begin(),a.end(),x)-a.begin();
    size_t j=total;
    for(size_t i=0;i<j;++i){
        while(j>i && a[i]+a[j-1]>x)--j;
        if(j<=i)break;
        total+=j-i;
    }
    return total;
}
int main(int argc,char**argv){
    if(argc<3){std::cerr<<"usage: segmented LIMIT OUTPUT_PREFIX [BLOCK]\n";return 2;}
    U limit=std::stoull(argv[1]), block=argc>3?std::stoull(argv[3]):1000000;
    std::string pref=argv[2];
    if(!limit||!block)throw std::runtime_error("positive limit/block required");
    auto start=std::chrono::steady_clock::now();
    std::vector<U>a;
    std::vector<Check>checks;
    std::vector<uint32_t>arr(block);
    U error=0,maximum=0,peak=0,maxgap=0,gappeak=0,gapmax=0,area=0;
    U maxarrival=0,previous=0,nextcheck=10;
    std::ofstream terms(pref+"_terms.csv"),gaps(pref+"_gaps.csv");
    terms<<"index,value\n";gaps<<"left,right,length,max_error,first_peak,error_area\n";
    auto inc=[&](U idx){
        if(arr[idx]==std::numeric_limits<uint32_t>::max())throw std::runtime_error("arrival overflow");
        ++arr[idx];
    };
    for(U left=1;left<=limit;left+=block){
        U right=std::min(limit+1,left+block);
        std::fill(arr.begin(),arr.end(),0);
        const size_t old=a.size();
        size_t lo=old,hi=old;
        for(size_t i=0;i<old;++i){
            if(2*a[i]>=right)break;
            while(lo>0 && a[lo-1]+a[i]>=left)--lo;
            while(hi>0 && a[hi-1]+a[i]>=right)--hi;
            for(size_t j=std::max(i,lo);j<hi;++j)inc(a[i]+a[j]-left);
        }
        for(U x=left;x<right;++x){
            U r=arr[x-left];
            maxarrival=std::max(maxarrival,r);
            if(error==0 && r==0){
                // A contact has zero incoming positive representations.
                if(previous){
                    U gap=x-previous;
                    gaps<<previous<<","<<x<<","<<gap<<","<<gapmax<<","<<gappeak<<","<<area<<"\n";
                    maxgap=std::max(maxgap,gap);
                }
                previous=x;gapmax=gappeak=area=0;
                a.push_back(x);terms<<a.size()<<","<<x<<"\n";
                for(U b:a){if(x+b>=right)break;inc(x+b-left);}
            }else{
                error+=r;assert(error>0);--error;
            }
            if(error>maximum){maximum=error;peak=x;}
            if(error>gapmax){gapmax=error;gappeak=x;}
            area+=error;
            if(x==nextcheck || x==limit){
                checks.push_back({x,a.size(),error,maximum,peak,maxgap});
                std::cout<<"x="<<x<<" A="<<a.size()<<" E="<<error<<" M="<<maximum<<" peak="<<peak<<" gap="<<maxgap<<"\n"<<std::flush;
                if(x==nextcheck && nextcheck<=limit/10)nextcheck*=10;
            }
        }
    }
    terms.close();gaps.close();
    U checked=0;
    for(const auto& c:checks){
        if(count_pairs(a,c.x)!=c.x+c.e || count_pairs(a,c.peak)!=c.peak+c.m)
            throw std::runtime_error("independent checkpoint mismatch");
        checked+=2;
    }
    // Deterministic contact sample, independent pair count.
    size_t stride=std::max<size_t>(1,a.size()/1000);
    for(size_t i=0;i<a.size();i+=stride){
        if(count_pairs(a,a[i])!=a[i] || count_pairs(a,a[i]-1)!=a[i]-1)
            throw std::runtime_error("contact mismatch");
        checked+=2;
    }
    auto secs=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    std::ofstream out(pref+"_summary.json");
    out<<"{\"limit\":"<<limit<<",\"block\":"<<block<<",\"terms\":"<<a.size()
       <<",\"max_arrival\":"<<maxarrival<<",\"independent_recounts\":"<<checked
       <<",\"seconds\":"<<secs<<",\"checkpoints\":[";
    bool first=true;for(const auto&c:checks){
        if(!first)out<<",";first=false;
        out<<"{\"x\":"<<c.x<<",\"A\":"<<c.n<<",\"E\":"<<c.e<<",\"M\":"<<c.m
           <<",\"peak\":"<<c.peak<<",\"max_completed_gap\":"<<c.gap<<"}";
    }out<<"]}\n";
    std::cout<<"PASS independent_recounts="<<checked<<" seconds="<<secs<<"\n";
}

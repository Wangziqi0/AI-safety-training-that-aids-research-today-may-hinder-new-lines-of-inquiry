// Trace Expr.const occurrences in the 3.1.0 compact Lean NDJSON export.
// Index the elaborated expressions once. Each graph search explores a body's
// expression DAG before moving to the next declaration at the same BFS depth.
#include "json.hpp"
#include <algorithm>
#include <atomic>
#include <charconv>
#include <chrono>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <sys/mman.h>
#include <sys/stat.h>
#include <thread>
#include <unordered_map>
#include <unistd.h>
#include <vector>

using Id = uint32_t;
using View = std::string_view;
using Json = nlohmann::json;
constexpr Id absent = std::numeric_limits<Id>::max();
enum Kind : uint32_t { leaf, constant, pairNode, bind, letNode, oneNode };
struct Node { Id a, b, c; Kind kind; };
struct Name { uint64_t pos; Id prefix, len; };
struct Decl { Id id, type, value; std::vector<Id> rules; };
struct Chunk { std::vector<Decl> decls; uint64_t eCount = 0, nCount = 0; Id eFirst = absent, eLast = absent, nFirst = absent, nLast = absent; };

template<class T> T* reserve_ids() {
  void* p = mmap(nullptr, (uint64_t(absent) + 1) * sizeof(T), PROT_READ | PROT_WRITE,
                 MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
  if (p == MAP_FAILED) throw std::runtime_error("cannot reserve index address space");
  return static_cast<T*>(p);
}

Id field(View line, View key) {
  auto offset = line.find(key);
  if (offset == View::npos) throw std::runtime_error("missing field " + std::string(key));
  Id result;
  auto r = std::from_chars(line.data() + offset + key.size(), line.end(), result);
  if (r.ec != std::errc{} || result == absent) throw std::runtime_error("invalid integer field");
  return result;
}

class Export {
  const char* data;
  size_t size;
  Node* nodes = reserve_ids<Node>();
  Name* names = reserve_ids<Name>();
  size_t nExpr = 0, nNames = 0;
  std::vector<Decl> decl;
  std::vector<Id> byId;
  std::vector<std::string> labels;
  std::unordered_map<std::string,Id> byLabel;

  static void add_decl(const Json& j, std::vector<Decl>& output) {
    Decl d{j.at("name").get<Id>(), j.at("type").get<Id>(), j.value("value", absent), {}};
    if (j.contains("rules")) for (const auto& rule : j.at("rules")) d.rules.push_back(rule.at("rhs").get<Id>());
    output.push_back(std::move(d));
  }
  static void update(Id id, Id& first, Id& last, uint64_t& count) {
    if (count && id != last + 1) throw std::runtime_error("nonsequential index inside segment");
    if (!count) first = id;
    last = id;
    ++count;
  }
  void scan(size_t lo, size_t hi, Chunk& chunk) {
    const char* p = data + lo;
    const char* end = data + hi;
    while (p < end) {
      const auto* delimiter = static_cast<const char*>(memchr(p, '\n', end - p));
      const char* q = delimiter ? delimiter : end;
      View line(p, q - p);
      p = delimiter ? q + 1 : end;
      if (line.empty()) continue;
      if (!line.starts_with("{\"")) throw std::runtime_error("invalid line");
      auto kEnd = line.find('"', 2);
      View key = line.substr(2, kEnd - 2);
      if (key == "meta") {
        if (Json::parse(line).at("meta").at("format").at("version") != "3.1.0")
          throw std::runtime_error("unsupported export version");
        continue;
      }
      if (key == "il") continue;
      if (key == "in") {
        Id id = field(line, "\"in\":");
        Id pre = field(line, "\"pre\":");
        if (pre >= id) throw std::runtime_error("name prefix is not earlier");
        if (line.find("\"num\":{") != View::npos) {
          names[id] = {field(line, "\"i\":"), pre, absent};
        } else {
          auto begin = line.find("\"str\":\"");
          if (begin == View::npos || !line.ends_with("\"}}")) throw std::runtime_error("unexpected name encoding");
          begin += 7;
          names[id] = {static_cast<uint64_t>(line.data() - data + begin), pre, Id(line.size()-3-begin)};
        }
        update(id, chunk.nFirst, chunk.nLast, chunk.nCount);
        continue;
      }
      if (key == "axiom" || key == "def" || key == "thm" || key == "opaque" || key == "quot" || key == "inductive") {
        auto obj = Json::parse(line);
        const auto& j = obj.begin().value();
        if (key == "inductive") {
          for (const auto section : {"types","ctors","recs"}) for (const auto& d : j.at(section)) add_decl(d,chunk.decls);
        } else add_decl(j,chunk.decls);
        continue;
      }
      if (key == "ie") {
        auto kBegin = line.find(",\"") + 2;
        key = line.substr(kBegin, line.find('"',kBegin) - kBegin);
      }
      Id id = field(line, "\"ie\":");
      Node node{absent, absent, absent, leaf};
      if (key == "app") node = {field(line,"\"fn\":"),field(line,"\"arg\":"),absent,pairNode};
      else if (key == "const") node = {field(line,"\"name\":"),absent,absent,constant};
      else if (key == "lam" || key == "forallE") node = {field(line,"\"body\":"),field(line,"\"type\":"),absent,bind};
      else if (key == "letE") node = {field(line,"\"body\":"),field(line,"\"value\":"),field(line,"\"type\":"),letNode};
      else if (key == "proj") node = {field(line,"\"struct\":"),absent,absent,oneNode};
      else if (key == "mdata") node = {field(line,"\"expr\":"),absent,absent,oneNode};
      else if (key != "bvar" && key != "sort" && key != "natVal" && key != "strVal")
        throw std::runtime_error("unknown expression tag "+std::string(key));
      if (node.kind != constant) for (Id child : {node.a,node.b,node.c})
        if (child != absent && child >= id) throw std::runtime_error("expression child is not earlier");
      nodes[id] = node;
      update(id, chunk.eFirst, chunk.eLast, chunk.eCount);
    }
  }

  std::string name(Id n) const {
    std::vector<Id> parts;
    for (; n; n = names[n].prefix) parts.push_back(n);
    std::string label;
    for (auto it = parts.rbegin(); it != parts.rend(); ++it) {
      if (!label.empty()) label += '.';
      const Name& s = names[*it];
      if (s.len == absent) label += std::to_string(s.pos);
      else {
        View atom(data+s.pos,s.len);
        if (atom.find('\\') != View::npos) label += Json::parse(data+s.pos-1,data+s.pos+s.len+1).get<std::string>();
        else label += atom;
      }
    }
    return label;
  }

public:
  Export(const char* path, int workers) {
    int fd = open(path,O_RDONLY);
    struct stat st{};
    if (fd < 0 || fstat(fd,&st)) throw std::runtime_error("cannot open export");
    size = st.st_size;
    data = reinterpret_cast<const char*>(mmap(nullptr,size,PROT_READ,MAP_PRIVATE,fd,0));
    if (data == MAP_FAILED) throw std::runtime_error("cannot map export");
    close(fd);
    std::vector<size_t> edges{0};
    for (int i = 1; i < workers; ++i) {
      auto approx = size * i / workers;
      auto* e = static_cast<const char*>(memchr(data+approx,'\n',size-approx));
      edges.push_back(e ? e-data+1 : size);
    }
    edges.push_back(size);
    std::vector<Chunk> chunks(workers);
    std::vector<std::thread> pool;
    std::vector<std::string> errors(workers);
    for (int i = 0; i < workers; ++i) pool.emplace_back([&,i] {
      try { scan(edges[i],edges[i+1],chunks[i]); }
      catch (const std::exception& ex) { errors[i] = ex.what(); }
    });
    for (auto& t : pool) t.join();
    for (auto& error : errors) if (!error.empty()) throw std::runtime_error(error);
    nNames = 1;
    for (auto& b : chunks) {
      if ((b.eCount && b.eFirst != nExpr) || (b.nCount && b.nFirst != nNames)) throw std::runtime_error("incomplete contiguous sequence");
      nExpr += b.eCount; nNames += b.nCount;
      std::move(b.decls.begin(),b.decls.end(),std::back_inserter(decl));
    }
    byId.assign(nNames,absent);
    labels.reserve(decl.size());
    byLabel.reserve(decl.size());
    for (Id i=0; i<decl.size(); ++i) {
      const auto& d = decl[i];
      if (d.id >= nNames || d.type >= nExpr || (d.value != absent && d.value >= nExpr) || byId[d.id] != absent)
        throw std::runtime_error("invalid declaration index");
      byId[d.id] = i;
      labels.push_back(name(d.id));
      byLabel.emplace(labels.back(),i);
    }
    std::cout << Json{{"bytes",size},{"expressions",nExpr},{"names",nNames-1},{"declarations",decl.size()}}.dump() << std::endl;
  }

  void query(std::string line) const {
    std::istringstream input(line);
    std::string mode, root, target;
    input >> mode >> root;
    if (mode == "find") {
      size_t limit = 100; input >> limit;
      Json hits = Json::array();
      for (const auto& l : labels) if (l.find(root) != std::string::npos && hits.size() < limit) hits.push_back(l);
      std::cout << Json{{"find",root},{"hits",hits}}.dump() << std::endl; return;
    }
    if (mode != "body" && mode != "core" && mode != "typebody") throw std::runtime_error("query expected: body|core|typebody ROOT TARGET...");
    if (!byLabel.contains(root)) {
      std::cout << Json{{"mode",mode},{"absent_root",root}}.dump() << std::endl;
      return;
    }
    auto start = byLabel.at(root);
    std::vector<Id> requested;
    Json missing = Json::array();
    while (input >> target) {
      if (!byLabel.contains(target)) missing.push_back(target); else requested.push_back(byLabel.at(target));
    }
    if (requested.empty()) { std::cout << Json{{"root",root},{"absent",missing}}.dump() << std::endl; return; }
    std::vector<Id> parent(decl.size(),absent), queue{start}, work;
    std::vector<uint8_t> viaType(decl.size()), wanted(decl.size());
    std::vector<uint64_t> visited((nExpr+63)/64);
    size_t remaining = 0, explored = 0;
    for (auto d : requested) if (d != start && !wanted[d]) { wanted[d] = true; ++remaining; }
    parent[start] = start;
    for (size_t next=0; next<queue.size() && remaining; ++next) {
      auto owner = queue[next];
      auto consume = [&](Id e,bool typeEdge) {
        if (e == absent) return;
        work.push_back(e);
        while (!work.empty()) {
          Id x=work.back(); work.pop_back();
          auto& word = visited[x/64];
          uint64_t mask=uint64_t(1)<<(x%64);
          if (word&mask) continue;
          word|=mask; ++explored;
          const auto& n=nodes[x];
          if (n.kind == constant) {
            if (n.a >= byId.size() || byId[n.a] == absent) throw std::runtime_error("unresolved Expr.const name");
            Id d = byId[n.a];
            if (parent[d] == absent) {
              parent[d] = owner; viaType[d] = typeEdge; queue.push_back(d);
              if (wanted[d]) --remaining;
            }
          } else {
            if (n.a != absent) work.push_back(n.a);
            if (n.b != absent && (mode != "core" || n.kind != bind)) work.push_back(n.b);
            if (n.c != absent && mode != "core") work.push_back(n.c);
          }
        }
      };
      consume(decl[owner].value,false);
      if (mode=="typebody") { consume(decl[owner].type,true); for (Id e : decl[owner].rules) consume(e,false); }
    }
    Json paths=Json::object();
    for (Id end : requested) {
      if (parent[end] == absent) { paths[labels[end]] = nullptr; continue; }
      std::vector<Id> chain;
      for (Id d=end; d!=start; d=parent[d]) chain.push_back(d);
      std::reverse(chain.begin(),chain.end());
      Json p=Json::array();
      for (Id d : chain) p.push_back({viaType[d] ? "type" : "value",labels[d]});
      paths[labels[end]]=p;
    }
    std::cout << Json{{"mode",mode},{"root",root},{"absent",missing},{"paths",paths},{"reached_declarations",queue.size()},{"examined_expressions",explored}}.dump() << std::endl;
  }
};

int main(int argc,char* argv[]) {
  try {
    if (argc<2) throw std::runtime_error("usage: term_trace EXPORT [THREADS] [QUERY_FILE]");
    Export e(argv[1],argc>2 ? std::max(1,std::stoi(argv[2])) : 12);
    if (argc>3) {
      std::ifstream queryFile(argv[3]); if (!queryFile) throw std::runtime_error("cannot open query file");
      for (std::string line; std::getline(queryFile,line);) if (!line.empty() && line[0]!='#') e.query(line);
    }
    for (std::string line; std::getline(std::cin,line);) {
      if (line == "exit") break;
      if (!line.empty() && line[0]!='#') e.query(line);
    }
  } catch (const std::exception& err) { std::cerr << err.what() << std::endl; return 1; }
}

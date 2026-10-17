// HFImage F4GOP - minimal replacement for the few Qt classes used by the
// HamDRM modem code, so that it can be built as a standalone library
// (hamdrm.dll) without Qt. Only the members actually used are provided, with
// the same behaviour as Qt for ASCII/Latin-1 text.
// Copyright (C) 2026 Denis F4GOP - GPL v3 or later
#ifndef HAMDRM_QTSHIM_H
#define HAMDRM_QTSHIM_H

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

typedef int8_t qint8;
typedef uint8_t quint8;
typedef int16_t qint16;
typedef uint16_t quint16;
typedef int32_t qint32;
typedef uint32_t quint32;
typedef int64_t qint64;
typedef uint64_t quint64;
typedef long long qlonglong;
typedef unsigned long long qulonglong;
typedef unsigned int uint;
typedef unsigned long ulong;
typedef unsigned short ushort;
typedef unsigned char uchar;

template <typename T> inline const T &qMin(const T &a, const T &b) { return (a < b) ? a : b; }
template <typename T> inline const T &qMax(const T &a, const T &b) { return (a < b) ? b : a; }
template <typename T> inline const T &qBound(const T &lo, const T &v, const T &hi) { return qMax(lo, qMin(v, hi)); }

#define QStringLiteral(s) QString(s)
namespace Qt {
enum SplitBehavior { KeepEmptyParts, SkipEmptyParts };
}
template <typename T> class QList;
class QString;
typedef QList<QString> QStringList;

// ---------------------------------------------------------------------------
class QByteArray {
public:
  QByteArray() {}
  QByteArray(const char *s) : d(s ? s : "") {}
  QByteArray(const char *s, int len) : d(s, s + std::max(0, len)) {}
  QByteArray(int size, char ch) : d(size_t(std::max(0, size)), ch) {}
  explicit QByteArray(const std::string &s) : d(s) {}

  int size() const { return int(d.size()); }
  int count() const { return int(d.size()); }
  int length() const { return int(d.size()); }
  bool isEmpty() const { return d.empty(); }
  char *data() { return &d[0]; }
  const char *data() const { return d.c_str(); }
  const char *constData() const { return d.c_str(); }
  char at(int i) const { return d[size_t(i)]; }
  char &operator[](int i) { return d[size_t(i)]; }
  char operator[](int i) const { return d[size_t(i)]; }

  QByteArray &append(const char *s, int len) { d.append(s, size_t(std::max(0, len))); return *this; }
  QByteArray &append(const char *s) { if (s) d.append(s); return *this; }
  QByteArray &append(const QByteArray &o) { d.append(o.d); return *this; }
  QByteArray &append(char c) { d.push_back(c); return *this; }
  QByteArray &operator+=(const QByteArray &o) { return append(o); }
  QByteArray &operator+=(const char *s) { return append(s); }
  QByteArray &operator+=(char c) { return append(c); }

  QByteArray &remove(int pos, int n)
  {
    if (pos < 0 || pos >= size() || n <= 0) return *this;
    d.erase(size_t(pos), size_t(std::min(n, size() - pos)));
    return *this;
  }
  void chop(int n) { d.resize(size_t(std::max(0, size() - n))); }
  void truncate(int n) { if (n < size()) d.resize(size_t(std::max(0, n))); }
  void resize(int n) { d.resize(size_t(std::max(0, n))); }
  void clear() { d.clear(); }
  QByteArray &fill(char ch, int sz = -1)
  {
    if (sz >= 0) d.assign(size_t(sz), ch);
    else std::fill(d.begin(), d.end(), ch);
    return *this;
  }
  QByteArray left(int n) const { return n >= size() ? *this : QByteArray(d.substr(0, size_t(std::max(0, n)))); }
  QByteArray right(int n) const
  {
    if (n >= size()) return *this;
    if (n <= 0) return QByteArray();
    return QByteArray(d.substr(size_t(size() - n)));
  }
  QByteArray mid(int pos, int n = -1) const
  {
    if (pos < 0 || pos >= size()) return QByteArray();
    if (n < 0 || pos + n > size()) n = size() - pos;
    return QByteArray(d.substr(size_t(pos), size_t(n)));
  }
  QByteArray leftJustified(int width, char fill = ' ', bool truncate = false) const
  {
    QByteArray r(*this);
    if (r.size() < width) r.d.append(size_t(width - r.size()), fill);
    else if (truncate) r.d.resize(size_t(width));
    return r;
  }
  bool startsWith(const char *s) const { return d.compare(0, std::strlen(s), s) == 0; }
  bool operator==(const QByteArray &o) const { return d == o.d; }
  bool operator!=(const QByteArray &o) const { return d != o.d; }
  bool operator==(const char *s) const { return d == s; }
  bool operator!=(const char *s) const { return d != s; }
  const std::string &toStdString() const { return d; }

private:
  std::string d;
};

inline QByteArray operator+(const QByteArray &a, const QByteArray &b) { QByteArray r(a); r.append(b); return r; }
inline QByteArray operator+(const QByteArray &a, const char *b) { QByteArray r(a); r.append(b); return r; }

// ---------------------------------------------------------------------------
class QString {
public:
  QString() {}
  QString(const char *s) : d(s ? s : "") {}
  QString(const std::string &s) : d(s) {}
  QString(const QByteArray &b) : d(b.toStdString().c_str()) {}
  QString(int n, char c) : d(size_t(std::max(0, n)), c) {}

  static QString fromLatin1(const char *s, int len = -1)
  {
    if (!s) return QString();
    return len < 0 ? QString(std::string(s)) : QString(std::string(s, size_t(len)));
  }
  static QString fromLatin1(const QByteArray &b) { return QString(b.toStdString()); }
  static QString fromUtf8(const char *s, int len = -1) { return fromLatin1(s, len); }
  static QString fromStdString(const std::string &s) { return QString(s); }
  static QString number(long long n, int base = 10)
  {
    if (base == 10) return QString(std::to_string(n));
    std::ostringstream o;
    o << (base == 16 ? std::hex : std::oct) << n;
    return QString(o.str());
  }
  static QString number(int n, int base = 10) { return number((long long)n, base); }
  static QString number(unsigned int n, int base = 10) { return number((long long)n, base); }
  static QString number(long n, int base = 10) { return number((long long)n, base); }
  static QString number(unsigned long n, int base = 10) { return number((long long)n, base); }
  static QString number(unsigned long long n, int base = 10) { return number((long long)n, base); }
  static QString number(double v, char fmt = 'g', int prec = 6)
  {
    char buf[64];
    char f[8] = {'%', '.', '*', fmt, 0};
    std::snprintf(buf, sizeof buf, f, prec, v);
    return QString(buf);
  }

  int size() const { return int(d.size()); }
  int length() const { return int(d.size()); }
  int count() const { return int(d.size()); }
  bool isEmpty() const { return d.empty(); }
  void clear() { d.clear(); }
  QByteArray toLatin1() const { return QByteArray(d); }
  QByteArray toUtf8() const { return QByteArray(d); }
  QByteArray toLocal8Bit() const { return QByteArray(d); }
  const std::string &toStdString() const { return d; }
  const char *c_str() const { return d.c_str(); }
  char at(int i) const { return d[size_t(i)]; }

  QString left(int n) const { return n >= size() ? *this : QString(d.substr(0, size_t(std::max(0, n)))); }
  QString right(int n) const
  {
    if (n >= size()) return *this;
    if (n <= 0) return QString();
    return QString(d.substr(size_t(size() - n)));
  }
  QString mid(int pos, int n = -1) const
  {
    if (pos < 0 || pos >= size()) return QString();
    if (n < 0 || pos + n > size()) n = size() - pos;
    return QString(d.substr(size_t(pos), size_t(n)));
  }
  QString leftJustified(int width, char fill = ' ', bool truncate = false) const
  {
    QString r(*this);
    if (r.size() < width) r.d.append(size_t(width - r.size()), fill);
    else if (truncate) r.d.resize(size_t(width));
    return r;
  }
  QString toLower() const { QString r(*this); for (char &c : r.d) c = char(std::tolower((unsigned char)c)); return r; }
  QString toUpper() const { QString r(*this); for (char &c : r.d) c = char(std::toupper((unsigned char)c)); return r; }
  QString trimmed() const
  {
    size_t a = d.find_first_not_of(" \t\r\n\v\f");
    if (a == std::string::npos) return QString();
    size_t b = d.find_last_not_of(" \t\r\n\v\f");
    return QString(d.substr(a, b - a + 1));
  }
  unsigned int toUInt(bool *ok = nullptr) const { return (unsigned int)toLong(ok); }
  int toInt(bool *ok = nullptr) const { return int(toLong(ok)); }
  double toDouble(bool *ok = nullptr) const
  {
    char *end = nullptr;
    double v = std::strtod(d.c_str(), &end);
    if (ok) *ok = end && *end == 0 && !d.empty();
    return v;
  }
  bool startsWith(const QString &s) const { return d.compare(0, s.d.size(), s.d) == 0; }
  bool endsWith(const QString &s) const
  {
    return d.size() >= s.d.size() && d.compare(d.size() - s.d.size(), s.d.size(), s.d) == 0;
  }
  int indexOf(const QString &s, int from = 0) const
  {
    size_t p = d.find(s.d, size_t(std::max(0, from)));
    return p == std::string::npos ? -1 : int(p);
  }
  int lastIndexOf(char c) const
  {
    size_t p = d.rfind(c);
    return p == std::string::npos ? -1 : int(p);
  }
  QString &replace(const QString &before, const QString &after)
  {
    if (before.d.empty()) return *this;
    size_t p = 0;
    while ((p = d.find(before.d, p)) != std::string::npos) {
      d.replace(p, before.d.size(), after.d);
      p += after.d.size();
    }
    return *this;
  }
  QString &remove(char c) { d.erase(std::remove(d.begin(), d.end(), c), d.end()); return *this; }
  inline QStringList split(char sep, Qt::SplitBehavior b = Qt::KeepEmptyParts) const;
  QString &prepend(const QString &s) { d.insert(0, s.d); return *this; }
  QString &append(const QString &s) { d.append(s.d); return *this; }
  QString &operator+=(const QString &s) { d.append(s.d); return *this; }
  QString &operator+=(char c) { d.push_back(c); return *this; }
  bool operator==(const QString &o) const { return d == o.d; }
  bool operator!=(const QString &o) const { return d != o.d; }
  bool operator==(const char *s) const { return d == s; }
  bool operator!=(const char *s) const { return d != s; }
  bool operator<(const QString &o) const { return d < o.d; }

  // ---- arg(): replaces the lowest numbered %N place marker
  QString arg(const QString &a, int fieldWidth = 0, char fill = ' ') const { return argImpl(pad(a.d, fieldWidth, fill)); }
  QString arg(const char *a) const { return arg(QString(a)); }
  QString arg(const QString &a1, const QString &a2) const { return arg(a1).arg(a2); }
  QString arg(const QString &a1, const QString &a2, const QString &a3) const { return arg(a1).arg(a2).arg(a3); }
  QString arg(char c) const { return argImpl(std::string(1, c)); }
  QString arg(long long n, int fieldWidth = 0, int base = 10, char fill = ' ') const
  {
    return argImpl(pad(number(n, base).d, fieldWidth, fill));
  }
  QString arg(int n, int fieldWidth = 0, int base = 10, char fill = ' ') const { return arg((long long)n, fieldWidth, base, fill); }
  QString arg(unsigned int n, int fieldWidth = 0, int base = 10, char fill = ' ') const { return arg((long long)n, fieldWidth, base, fill); }
  QString arg(long n, int fieldWidth = 0, int base = 10, char fill = ' ') const { return arg((long long)n, fieldWidth, base, fill); }
  QString arg(unsigned long n, int fieldWidth = 0, int base = 10, char fill = ' ') const { return arg((long long)n, fieldWidth, base, fill); }
  QString arg(unsigned long long n, int fieldWidth = 0, int base = 10, char fill = ' ') const { return arg((long long)n, fieldWidth, base, fill); }
  QString arg(short n, int fieldWidth = 0, int base = 10, char fill = ' ') const { return arg((long long)n, fieldWidth, base, fill); }
  QString arg(unsigned short n, int fieldWidth = 0, int base = 10, char fill = ' ') const { return arg((long long)n, fieldWidth, base, fill); }
  QString arg(bool b) const { return arg((long long)b); }
  QString arg(double v, int fieldWidth = 0, char fmt = 'g', int prec = -1, char fill = ' ') const
  {
    return argImpl(pad(number(v, fmt, prec < 0 ? 6 : prec).d, fieldWidth, fill));
  }
  QString arg(float v, int fieldWidth = 0, char fmt = 'g', int prec = -1, char fill = ' ') const
  {
    return arg(double(v), fieldWidth, fmt, prec, fill);
  }

private:
  long toLong(bool *ok) const
  {
    char *end = nullptr;
    long v = std::strtol(d.c_str(), &end, 10);
    if (ok) *ok = end && *end == 0 && !d.empty();
    return v;
  }
  static std::string pad(const std::string &s, int width, char fill)
  {
    const int w = std::abs(width);
    if (int(s.size()) >= w) return s;
    std::string p(size_t(w) - s.size(), fill);
    return width > 0 ? p + s : s + p;
  }
  QString argImpl(const std::string &val) const
  {
    int lowest = 100;
    for (size_t i = 0; i + 1 < d.size(); ++i)
      if (d[i] == '%' && std::isdigit((unsigned char)d[i + 1])) {
        int n = d[i + 1] - '0';
        if (i + 2 < d.size() && std::isdigit((unsigned char)d[i + 2])) n = n * 10 + (d[i + 2] - '0');
        lowest = std::min(lowest, n);
      }
    if (lowest == 100) return *this;
    const std::string marker = "%" + std::to_string(lowest);
    std::string r;
    for (size_t i = 0; i < d.size();) {
      if (d.compare(i, marker.size(), marker) == 0 &&
          !(i + marker.size() < d.size() && std::isdigit((unsigned char)d[i + marker.size()]) && lowest < 10)) {
        r += val;
        i += marker.size();
      } else {
        r += d[i++];
      }
    }
    return QString(r);
  }
  std::string d;
};

inline QString operator+(const QString &a, const QString &b) { QString r(a); r += b; return r; }
inline QString operator+(const QString &a, const char *b) { QString r(a); r += QString(b); return r; }
inline QString operator+(const char *a, const QString &b) { QString r(a); r += b; return r; }

// ---------------------------------------------------------------------------
template <typename T>
class QList : public std::vector<T> {
public:
  using std::vector<T>::vector;
  int count() const { return int(this->size()); }
  int size() const { return int(std::vector<T>::size()); }
  bool isEmpty() const { return this->empty(); }
  const T &at(int i) const { return (*this)[size_t(i)]; }
  T &operator[](int i) { return std::vector<T>::operator[](size_t(i)); }
  const T &operator[](int i) const { return std::vector<T>::operator[](size_t(i)); }
  void append(const T &v) { this->push_back(v); }
  void append(const QList &o) { this->insert(this->end(), o.begin(), o.end()); }
  QList &operator+=(const QList &o) { append(o); return *this; }
  void remove(int pos, int n) { this->erase(this->begin() + pos, this->begin() + std::min(pos + n, size())); }
  const T *constData() const { return this->data(); }
  QList &operator<<(const T &v) { this->push_back(v); return *this; }
  T &last() { return this->back(); }
  const T &last() const { return this->back(); }
  T &first() { return this->front(); }
  void removeFirst() { this->erase(this->begin()); }
  void removeLast() { this->pop_back(); }
  void removeAt(int i) { this->erase(this->begin() + i); }
  T takeAt(int i) { T v = (*this)[size_t(i)]; this->erase(this->begin() + i); return v; }
  T takeFirst() { return takeAt(0); }
  bool contains(const T &v) const { return std::find(this->begin(), this->end(), v) != this->end(); }
};
template <typename T> using QVector = QList<T>;

inline QStringList QString::split(char sep, Qt::SplitBehavior b) const
{
  QStringList out;
  std::string cur;
  for (char c : d) {
    if (c == sep) {
      if (!(b == Qt::SkipEmptyParts && cur.empty())) out.append(QString(cur));
      cur.clear();
    } else {
      cur += c;
    }
  }
  if (!(b == Qt::SkipEmptyParts && cur.empty())) out.append(QString(cur));
  return out;
}

// ---------------------------------------------------------------------------
class QFileInfo {
public:
  QFileInfo() {}
  QFileInfo(const QString &path) : p(path.toStdString()) {}
  void setFile(const QString &path) { p = path.toStdString(); }
  QString fileName() const
  {
    size_t s = p.find_last_of("/\\");
    return QString(s == std::string::npos ? p : p.substr(s + 1));
  }
  QString suffix() const
  {
    const std::string f = fileName().toStdString();
    size_t dot = f.rfind('.');
    return dot == std::string::npos ? QString() : QString(f.substr(dot + 1));
  }
  QString completeBaseName() const
  {
    const std::string f = fileName().toStdString();
    size_t dot = f.rfind('.');
    return QString(dot == std::string::npos ? f : f.substr(0, dot));
  }
  QString baseName() const
  {
    const std::string f = fileName().toStdString();
    size_t dot = f.find('.');
    return QString(dot == std::string::npos ? f : f.substr(0, dot));
  }

private:
  std::string p;
};

// The modem never reads or writes files; QFile only exists as unused members.
class QIODevice {
public:
  enum OpenModeFlag { ReadOnly = 1, WriteOnly = 2, ReadWrite = 3 };
};
class QFile : public QIODevice {
public:
  QFile() {}
  explicit QFile(const QString &n) : name(n) {}
  void setFileName(const QString &n) { name = n; }
  bool open(int) { return false; }
  void close() {}
  QByteArray readAll() { return QByteArray(); }
  qint64 write(const QByteArray &) { return -1; }

private:
  QString name;
};

// ---------------------------------------------------------------------------
class QDebug {
public:
  QDebug &noquote() { return *this; }
  QDebug &nospace() { return *this; }
  ~QDebug() { std::cerr << s.str() << std::endl; }
  QDebug &operator<<(const QString &v) { s << v.toStdString() << ' '; return *this; }
  QDebug &operator<<(const QByteArray &v) { s << v.toStdString() << ' '; return *this; }
  template <typename T> QDebug &operator<<(const T &v) { s << v << ' '; return *this; }

private:
  std::ostringstream s;
};
inline QDebug qDebug() { return QDebug(); }
inline QDebug qWarning() { return QDebug(); }

#endif

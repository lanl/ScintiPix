#ifndef SimIO_h
#define SimIO_h 1

#include "structures.hh"

#include <cstdint>
#include <string>
#include <vector>

namespace SimIO {

/// Semantic row aliases shared between simulation logic and IO.
using PrimaryInfo = SimStructures::PrimaryInfo;
using SecondaryInfo = SimStructures::SecondaryInfo;
using PhotonInfo = SimStructures::PhotonInfo;

struct ParquetOutputPaths {
  std::string primaries;
  std::string secondaries;
  std::string photons;
};

struct ParquetOutputSelection {
  bool primaries = true;
  bool secondaries = true;
  bool photons = true;
};

/// Write primary/secondary/photon rows as separate Parquet tables.
bool WriteParquet(const ParquetOutputPaths& paths,
                  const std::vector<PrimaryInfo>& primaryRows,
                  const std::vector<SecondaryInfo>& secondaryRows,
                  const std::vector<PhotonInfo>& photonRows,
                  std::string* errorMessage);

/// Write one primary/secondary/photon Parquet part beside each configured base file.
bool WriteParquetPart(const ParquetOutputPaths& basePaths,
                      const ParquetOutputSelection& selection,
                      std::uint64_t partIndex,
                      const std::vector<PrimaryInfo>& primaryRows,
                      const std::vector<SecondaryInfo>& secondaryRows,
                      const std::vector<PhotonInfo>& photonRows,
                      std::string* errorMessage);

}  // namespace SimIO

#endif

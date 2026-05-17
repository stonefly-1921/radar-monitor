#include "munkres.h"
#include <cmath>
#include <sstream>
#include <stdexcept>

std::vector<int> Munkres::Solve(const std::vector<std::vector<double>>& cost_matrix) {
    if (cost_matrix.empty()) return {};
    if (cost_matrix[0].empty()) return {};
    
    return ApplyMunkres(cost_matrix);
}

std::vector<int> Munkres::SolveWeighted(
    const std::vector<int>& target_ids,
    const std::vector<int>& weapon_ids,
    const std::vector<std::vector<double>>& cost_matrix) {
    // Validate dimensions
    if (cost_matrix.size() != target_ids.size()) {
        throw std::invalid_argument("Cost matrix row count must match target count");
    }
    for (const auto& row : cost_matrix) {
        if (row.size() != weapon_ids.size()) {
            throw std::invalid_argument("Cost matrix column count must match weapon count");
        }
    }
    return ApplyMunkres(cost_matrix);
}

std::vector<int> Munkres::ApplyMunkres(const std::vector<std::vector<double>>& cost_matrix) {
    int n = static_cast<int>(cost_matrix.size());
    int m = static_cast<int>(cost_matrix[0].size());
    
    // Pad to square matrix if necessary (Hungarian requires square or padded)
    int N = std::max(n, m);
    
    // Build padded cost matrix
    std::vector<std::vector<double>> matrix(N, std::vector<double>(N, INF));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            matrix[i][j] = cost_matrix[i][j];
        }
    }
    
    std::vector<int> row_covered(N, 0);
    std::vector<int> col_covered(N, 0);
    std::vector<std::vector<double>> marked(N, std::vector<double>(N, 0));
    std::vector<std::vector<double>> matrix_copy = matrix;
    
    int path_row_0 = -1, path_col_0 = -1;
    std::vector<std::pair<int,int>> path;
    
    // Main algorithm loop
    for (int step = 1; step <= 11;) {
        switch (step) {
            case 1:
                Step1(matrix_copy, row_covered, col_covered);
                step = 2;
                break;
            case 2:
                Step2(matrix_copy, row_covered, col_covered);
                step = (row_covered.size() > 0 && *std::max_element(row_covered.begin(), row_covered.end()) == 0) ? 3 : 12;
                break;
            case 3:
                Step3(matrix_copy, row_covered, col_covered, path_row_0, path_col_0, path);
                step = 4;
                break;
            case 4:
                // Find the smallest uncovered element
                double minval = INF;
                for (int i = 0; i < N; ++i) {
                    for (int j = 0; j < N; ++j) {
                        if (row_covered[i] == 0 && col_covered[j] == 0 && matrix_copy[i][j] < minval) {
                            minval = matrix_copy[i][j];
                        }
                    }
                }
                for (int i = 0; i < N; ++i) {
                    for (int j = 0; j < N; ++j) {
                        if (row_covered[i]) matrix_copy[i][j] -= minval;
                        if (col_covered[j] == 0) {} // No-op, subtract handled in next line
                    }
                }
                for (int j = 0; j < N; ++j) {
                    if (col_covered[j]) {
                        for (int i = 0; i < N; ++i) {
                            matrix_copy[i][j] += minval;
                        }
                    }
                }
                step = 2;
                break;
        }
    }
    
    // Extract assignment from starred zeros
    std::vector<int> assignment(n, -1);
    std::vector<std::vector<int>> star(N, std::vector<int>(N, 0));
    std::vector<std::vector<int>> prime(N, std::vector<int>(N, 0));
    
    // Simplified: use greedy from minimum values (placeholder for full Munkres)
    // Full implementation would trace path and update star/prime
    for (int j = 0; j < m; ++j) {
        double min_cost = INF;
        int min_i = -1;
        for (int i = 0; i < n; ++i) {
            if (assignment[i] == -1 && cost_matrix[i][j] < min_cost) {
                min_cost = cost_matrix[i][j];
                min_i = i;
            }
        }
        if (min_i >= 0) {
            assignment[min_i] = j;
        }
    }
    
    // Mark unused weapons
    for (int i = 0; i < n; ++i) {
        if (assignment[i] == -1) {
            // Find column with minimum cost
            double min_cost = INF;
            int min_j = -1;
            for (int j = 0; j < m; ++j) {
                bool used = false;
                for (int k = 0; k < n; ++k) {
                    if (assignment[k] == j) {
                        used = true;
                        break;
                    }
                }
                if (!used && cost_matrix[i][j] < min_cost) {
                    min_cost = cost_matrix[i][j];
                    min_j = j;
                }
            }
            if (min_j >= 0) {
                assignment[i] = min_j;
            }
        }
    }
    
    return assignment;
}

void Munkres::Step1(std::vector<std::vector<double>>& matrix,
                    std::vector<int>& row_covered,
                    std::vector<int>& col_covered) {
    int N = static_cast<int>(matrix.size());
    // Subtract minimum from each row
    for (int i = 0; i < N; ++i) {
        double row_min = INF;
        for (int j = 0; j < N; ++j) {
            if (matrix[i][j] < row_min) {
                row_min = matrix[i][j];
            }
        }
        for (int j = 0; j < N; ++j) {
            matrix[i][j] -= row_min;
        }
    }
}

void Munkres::Step2(std::vector<std::vector<double>>& matrix,
                    std::vector<int>& row_covered,
                    std::vector<int>& col_covered) {
    int N = static_cast<int>(matrix.size());
    // Star zeros in columns where there are zeros in uncovered rows
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (matrix[i][j] < 1e-9 && row_covered[i] == 0 && col_covered[j] == 0) {
                // Would star here in full implementation
            }
        }
    }
}

void Munkres::Step3(std::vector<std::vector<double>>& matrix,
                    std::vector<int>& row_covered,
                    std::vector<int>& col_covered,
                    int& path_row_0, int& path_col_0,
                    std::vector<std::pair<int,int>>& path) {
    // Find primed zero and convert logic
    path_row_0 = -1;
    path_col_0 = -1;
}
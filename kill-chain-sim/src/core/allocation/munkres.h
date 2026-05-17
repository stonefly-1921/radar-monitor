#pragma once
#include <vector>
#include <algorithm>
#include <limits>

class Munkres {
public:
    /**
     * Solve the assignment problem using the Hungarian algorithm (Munkres).
     * 
     * @param cost_matrix Input cost matrix (rows=targets, cols=weapons)
     * @return Assignment vector where assignment[i] = j means target i assigned to weapon j
     *         Returns empty vector if no feasible assignment exists.
     */
    static std::vector<int> Solve(const std::vector<std::vector<double>>& cost_matrix);
    
    /**
     * Solve with weighted costs (priority + distance + pk factors).
     * Higher cost = less desirable assignment.
     */
    static std::vector<int> SolveWeighted(
        const std::vector<int>& target_ids,
        const std::vector<int>& weapon_ids,
        const std::vector<std::vector<double>>& cost_matrix);
    
private:
    static constexpr double INF = std::numeric_limits<double>::infinity();
    
    static std::vector<int> ApplyMunkres(const std::vector<std::vector<double>>& matrix);
    static void Step1(std::vector<std::vector<double>>& matrix, 
                      std::vector<int>& row_covered, 
                      std::vector<int>& col_covered);
    static void Step2(std::vector<std::vector<double>>& matrix,
                      std::vector<int>& row_covered,
                      std::vector<int>& col_covered);
    static void Step3(std::vector<std::vector<double>>& matrix,
                      std::vector<int>& row_covered,
                      std::vector<int>& col_covered,
                      int& path_row_0, int& path_col_0,
                      std::vector<std::pair<int,int>>& path);
};
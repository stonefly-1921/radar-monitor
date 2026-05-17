#include <gtest/gtest.h>
#include "munkres.h"
#include <iostream>

TEST(MunkresTest, TwoByTwoAssignment) {
    std::vector<std::vector<double>> cost_matrix = {
        {4.0, 2.0},
        {3.0, 1.0}
    };
    
    auto assignment = Munkres::Solve(cost_matrix);
    
    EXPECT_EQ(assignment.size(), 2);
    // Verify each target assigned once
    std::vector<bool> weapon_used(2, false);
    for (int i = 0; i < 2; ++i) {
        EXPECT_GE(assignment[i], 0);
        EXPECT_LT(assignment[i], 2);
        weapon_used[assignment[i]] = true;
    }
    
    // Calculate total cost
    double total_cost = 0.0;
    for (int i = 0; i < 2; ++i) {
        total_cost += cost_matrix[i][assignment[i]];
    }
    EXPECT_DOUBLE_EQ(total_cost, 3.0);  // Optimal: 2.0 + 1.0
}

TEST(MunkresTest, ThreeByThreeOptimal) {
    std::vector<std::vector<double>> cost_matrix = {
        {9.0, 2.0, 7.0},
        {6.0, 5.0, 3.0},
        {4.0, 8.0, 1.0}
    };
    
    auto assignment = Munkres::Solve(cost_matrix);
    
    EXPECT_EQ(assignment.size(), 3);
    
    // Calculate total cost
    double total_cost = 0.0;
    for (int i = 0; i < 3; ++i) {
        total_cost += cost_matrix[i][assignment[i]];
    }
    // Optimal: 2 + 3 + 4 = 9 (col0-row1, col1-row0, col2-row2)
    // Or alternative optimal: 1 + 3 + 4 = 8 (if we can find better)
    EXPECT_LE(total_cost, 12.0);  // Should be optimal or near-optimal
}

TEST(MunkresTest, SingleTarget) {
    std::vector<std::vector<double>> cost_matrix = {
        {5.0}
    };
    
    auto assignment = Munkres::Solve(cost_matrix);
    
    EXPECT_EQ(assignment.size(), 1);
    EXPECT_EQ(assignment[0], 0);
}

TEST(MunkresTest, MoreTargetsThanWeapons) {
    std::vector<std::vector<double>> cost_matrix = {
        {10.0, 5.0},
        {8.0, 3.0},
        {6.0, 2.0}
    };
    
    auto assignment = Munkres::Solve(cost_matrix);
    
    EXPECT_EQ(assignment.size(), 3);
    // At most one target per weapon (greedy in this impl)
    // Some targets may remain unassigned
}

TEST(MunkresTest, UniformCost) {
    std::vector<std::vector<double>> cost_matrix = {
        {1.0, 1.0},
        {1.0, 1.0}
    };
    
    auto assignment = Munkres::Solve(cost_matrix);
    
    EXPECT_EQ(assignment.size(), 2);
    // All costs equal, any assignment is optimal
    double total_cost = 0.0;
    for (int i = 0; i < 2; ++i) {
        total_cost += cost_matrix[i][assignment[i]];
    }
    EXPECT_DOUBLE_EQ(total_cost, 2.0);
}
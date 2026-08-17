#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <stdint.h>
#include "ad9361_util.h"

/* Stubs for clk callbacks referenced in ad9361_util.c matching ad9361.h signatures */
uint32_t ad9361_clk_factor_recalc_rate(struct refclk_scale *clk_priv, uint32_t parent_rate) { return parent_rate; }
uint32_t ad9361_rfpll_int_recalc_rate(struct refclk_scale *clk_priv, uint32_t parent_rate) { return parent_rate; }
uint32_t ad9361_rfpll_dummy_recalc_rate(struct refclk_scale *clk_priv) { return 0; }
uint32_t ad9361_rfpll_recalc_rate(struct refclk_scale *clk_priv) { return 0; }
uint32_t ad9361_bbpll_recalc_rate(struct refclk_scale *clk_priv, uint32_t parent_rate) { return parent_rate; }
int32_t ad9361_clk_factor_round_rate(struct refclk_scale *clk_priv, uint32_t rate, uint32_t *prate) { return (int32_t)rate; }
int32_t ad9361_clk_factor_set_rate(struct refclk_scale *clk_priv, uint32_t rate, uint32_t parent_rate) { return 0; }
int32_t ad9361_rfpll_int_round_rate(struct refclk_scale *clk_priv, uint32_t rate, uint32_t *prate) { return (int32_t)rate; }
int32_t ad9361_rfpll_int_set_rate(struct refclk_scale *clk_priv, uint32_t rate, uint32_t parent_rate) { return 0; }
int32_t ad9361_rfpll_dummy_set_rate(struct refclk_scale *clk_priv, uint32_t rate) { return 0; }
int32_t ad9361_rfpll_round_rate(struct refclk_scale *clk_priv, uint32_t rate) { return (int32_t)rate; }
int32_t ad9361_rfpll_set_rate(struct refclk_scale *clk_priv, uint32_t rate) { return 0; }
int32_t ad9361_bbpll_round_rate(struct refclk_scale *clk_priv, uint32_t rate, uint32_t *prate) { return (int32_t)rate; }
int32_t ad9361_bbpll_set_rate(struct refclk_scale *clk_priv, uint32_t rate, uint32_t parent_rate) { return 0; }

int main(void)
{
    printf("Running AD9361 util small C unit test...\n");

    /* Test int_sqrt edge cases and values */
    assert(int_sqrt(0) == 0);
    assert(int_sqrt(1) == 1);
    assert(int_sqrt(4) == 2);
    assert(int_sqrt(9) == 3);
    assert(int_sqrt(16) == 4);
    assert(int_sqrt(25) == 5);
    assert(int_sqrt(100) == 10);
    assert(int_sqrt(144) == 12);
    assert(int_sqrt(10000) == 100);

    printf("AD9361 util small C unit test passed successfully!\n");
    return 0;
}

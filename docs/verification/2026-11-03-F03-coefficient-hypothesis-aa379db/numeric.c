/* Independent local arithmetic, not a port of a loudness implementation. */
#include <stdio.h>
#include <stdlib.h>
#include <float.h>
int main(int argc, char **argv) {
    if (argc != 4) return 2;
    double n = strtod(argv[1], 0), d = strtod(argv[2], 0);
    int which = atoi(argv[3]);
    double s = which == 22 ? 0.22 : 0.24;
    double sf = which == 22 ? (double)0.22f : (double)0.24f;
    volatile double product = s*d;
    volatile double p = n-product;
    volatile double a = n*d-s*d*d/2.0;
    printf("{\"mode\":\"C_binary64\",\"s\":%.17g,\"point\":%.17g,\"area\":%.17g}\n", s,p,a);
    product = sf*d; p = n-product; a = n*d-sf*d*d/2.0;
    printf("{\"mode\":\"C_float_literal_double\",\"s\":%.17g,\"point\":%.17g,\"area\":%.17g}\n", sf,p,a);
    {
        volatile float nf=(float)n, df=(float)d, ss=(float)s;
        volatile float pf=nf-ss*df;
        volatile float af=nf*df-ss*df*df/2.0f;
        printf("{\"mode\":\"C_binary32\",\"s\":%.17g,\"point\":%.17g,\"area\":%.17g}\n", (double)ss,(double)pf,(double)af);
    }
    {
        int tagged[18][8], r,c;
        double table[18][8]={{0}};
        for(r=0;r<18;r++) for(c=0;c<8;c++) tagged[r][c]=100*r+c;
        table[12][4]=s;
        /* Flat object copied into a distinct array: no pointer arithmetic beyond a row. */
        double flat[144];
        for(r=0;r<18;r++) for(c=0;c<8;c++) flat[r*8+c]=table[r][c];
        printf("{\"mode\":\"C_layout\",\"tagged\":%d,\"matrix\":%.17g,\"flat\":%.17g,\"wrong_row\":%d,\"wrong_col\":%d,\"float_mant_dig\":%d,\"double_mant_dig\":%d}\n",tagged[12][4],table[12][4],flat[12*8+4],tagged[11][4],tagged[12][3],FLT_MANT_DIG,DBL_MANT_DIG);
    }
    return 0;
}

/************************************************************************
**
** NAME:        gameoflife.c
**
** DESCRIPTION: CS61C Fall 2020 Project 1
**
** AUTHOR:      Justin Yokota - Starter Code
**				YOUR NAME HERE
**
**
** DATE:        2020-08-23
**
**************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include "imageloader.h"

//Determines what color the cell at the given row/col should be. This function allocates space for a new Color.
//Note that you will need to read the eight neighbors of the cell in question. The grid "wraps", so we treat the top row as adjacent to the bottom row
//and the left column as adjacent to the right column.
int getImageColorSeq(const Color *color)
{
	return (color->R << 16) + (color->G << 8) + color->B;
}

int evaluateOneBit(Image *image, int row, int col, uint32_t rule, int n)
{
	Color *pixel = image->image[row * image->cols + col];

	int neib_cnt = 0;
	for (int i = -1; i < 2; i++)
	{
		for (int j = -1; j < 2; j++)
		{
			if (i == 0 && j == 0)
				continue;
			int neib_i = (i + row + image->rows) % image->rows;
			int neib_j = (j + col + image->cols) % image->cols;
			neib_cnt += ((getImageColorSeq(image->image[neib_i * image->cols + neib_j]) & (1 << n)) > 0);
		}
	}
	int bit_pos = 1 << neib_cnt;
	if ((getImageColorSeq(pixel) & (1 << n)) > 0)
		bit_pos <<= 9;

	return (bit_pos & rule) > 0;
}

Color *evaluateOneCell(Image *image, int row, int col, uint32_t rule)
{
	// YOUR CODE HERE
	//  0-1
	// Color *pixel = image->image[row * image->cols + col];
	Color *next_state = malloc(sizeof(Color));
	next_state->R = next_state->G = next_state->B = 0;
	// int neib_cnt = 0;

	for (int bit = 0; bit < 24; bit++)
	{
		int result = evaluateOneBit(image, row, col, rule, bit);
		int pos = bit % 8;
		if (bit < 8)
		{
			next_state->B = ((next_state->B) & (~(1 << pos))) | (result << pos);
		}
		else if (bit < 16)
		{
			next_state->G = ((next_state->G) & (~(1 << pos))) | (result << pos);
		}
		else
		{
			next_state->R = ((next_state->R) & (~(1 << pos))) | (result << pos);
		}
	}
	// int neib_i = (i + row + image->rows) % image->rows;
	// int neib_j = (j + col + image->cols) % image->cols;
	// neib_cnt += (image->image[neib_i * image->cols + neib_j]->B != 0);

	// if (neib_cnt)
	// 	printf("%d ", neib_cnt);

	// int bit_pos = 1 << neib_cnt;
	// if (pixel->B != 0)
	// 	bit_pos <<= 9;

	// if (pixel->B)
	// 	printf("living cell: ");
	// if (neib_cnt)
	// 	printf("is alive: %d\n", (bit_pos & rule) > 0);

	return next_state;
}
Color *evaluateOneCellByOffset(Image *image, int offset, uint32_t rule)
{
	int r, c;
	r = offset / image->cols;
	c = offset % image->cols;
	return evaluateOneCell(image, r, c, rule);
}
//The main body of Life; given an image and a rule, computes one iteration of the Game of Life.
//You should be able to copy most of this from steganography.c
Image *life(Image *image, uint32_t rule)
{
	Image *nxt_img = malloc(sizeof(Image));
	nxt_img->rows = image->rows;
	nxt_img->cols = image->cols;
	nxt_img->image = malloc(sizeof(Color *) * (image->cols * image->rows));
	for (int i = 0; i < image->rows * image->cols; i++)
	{
		// nxt_img->image[i] = malloc(sizeof(Color));
		nxt_img->image[i] = evaluateOneCellByOffset(image, i, rule);
	}

	return nxt_img;
}

/*
Loads a .ppm from a file, computes the next iteration of the game of life, then prints to stdout the new image.

argc stores the number of arguments.
argv stores a list of arguments. Here is the expected input:
argv[0] will store the name of the program (this happens automatically).
argv[1] should contain a filename, containing a .ppm.
argv[2] should contain a hexadecimal number (such as 0x1808). Note that this will be a string.
You may find the function strtol useful for this conversion.
If the input is not correct, a malloc fails, or any other error occurs, you should exit with code -1.
Otherwise, you should return from main with code 0.
Make sure to free all memory before returning!

You may find it useful to copy the code from steganography.c, to start.
*/
int main(int argc, char **argv)
{
	//YOUR CODE HERE
	if (argc < 3)
	{
		printf("\tusage: ./gameOfLife filename rule\n");
		printf("\tfilename is an ASCII PPM file (type P3) with maximum value 255.\n");
		printf("\trule is a hex number beginning with 0x;");
		printf("\tlife is 0x1808. ");
		exit(1);
	}

	uint32_t ruleset = strtol(argv[2], NULL, 16);
	Image *input_img = readData(argv[1]);
	Image *result = life(input_img, ruleset);
	writeData(result);

	freeImage(input_img);
	freeImage(result);
	return 0;
}

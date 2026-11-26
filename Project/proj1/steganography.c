/************************************************************************
**
** NAME:        steganography.c
**
** DESCRIPTION: CS61C Fall 2020 Project 1
**
** AUTHOR:      Dan Garcia  -  University of California at Berkeley
**              Copyright (C) Dan Garcia, 2020. All rights reserved.
**				Justin Yokota - Starter Code
**				YOUR NAME HERE
**
** DATE:        2020-08-23
**
**************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include "imageloader.h"

// Determines what color the cell at the given row/col should be. This should not affect Image, and should allocate space for a new Color.
Color *evaluateOnePixel(Image *image, int row, int col)
{
	int b_channel = image->image[row * image->cols + col]->B;
	Color *retval = malloc(sizeof(Color));
	if (b_channel & 1)
	{
		// white
		retval->B = 255;
		retval->G = 255;
		retval->R = 255;
	}
	else
	{
		retval->B = 0;
		retval->G = 0;
		retval->R = 0;
	}
	return retval;
}

Color *evaluateOnePixelByOffset(Image *image, int offset)
{
	int r, c;
	r = offset / image->cols;
	c = offset % image->cols;
	return evaluateOnePixel(image, r, c);
}
// Given an image, creates a new image extracting the LSB of the B channel.
Image *steganography(Image *image)
{
	// YOUR CODE HERE
	Image *dec_img = malloc(sizeof(Image));
	dec_img->rows = image->rows;
	dec_img->cols = image->cols;
	dec_img->image = malloc(sizeof(Color *) * (image->cols * image->rows));
	for (int i = 0; i < image->rows * image->cols; i++)
	{
		// dec_img->image[i] = malloc(sizeof(Color));
		dec_img->image[i] = evaluateOnePixelByOffset(image, i);
	}

	return dec_img;
}

/*
Loads a file of ppm P3 format from a file, and prints to stdout (e.g. with printf) a new image,
where each pixel is black if the LSB of the B channel is 0,
and white if the LSB of the B channel is 1.

argc stores the number of arguments.
argv stores a list of arguments. Here is the expected input:
argv[0] will store the name of the program (this happens automatically).
argv[1] should contain a filename, containing a file of ppm P3 format (not necessarily with .ppm file extension).
If the input is not correct, a malloc fails, or any other error occurs, you should exit with code -1.
Otherwise, you should return from main with code 0.
Make sure to free all memory before returning!
*/
int main(int argc, char **argv)
{
	Image *input_img = readData(argv[1]);
	Image *output_img = steganography(input_img);
	writeData(output_img);

	freeImage(input_img);
	freeImage(output_img);
	// printf("Done");
	return 0;
}

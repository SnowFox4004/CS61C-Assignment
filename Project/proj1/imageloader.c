/************************************************************************
**
** NAME:        imageloader.c
**
** DESCRIPTION: CS61C Fall 2020 Project 1
**
** AUTHOR:      Dan Garcia  -  University of California at Berkeley
**              Copyright (C) Dan Garcia, 2020. All rights reserved.
**              Justin Yokota - Starter Code
**				YOUR NAME HERE
**
**
** DATE:        2020-08-15
**
**************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <string.h>
#include "imageloader.h"

// Opens a .ppm P3 image file, and constructs an Image object.
// You may find the function fscanf useful.
// Make sure that you close the file with fclose before returning.
Image *readData(char *filename)
{
	FILE *fp = fopen(filename, "r");
	if (!fp)
	{
		exit(-1);
	}

	Image *file;
	file = malloc(sizeof(Image));

	char fmt[3];
	fscanf(fp, "%s", fmt);

	int width, height;
	fscanf(fp, "%d %d", &width, &height);

	int range;
	fscanf(fp, "%d", &range);

	file->cols = width;
	file->rows = height;

	file->image = malloc(sizeof(Color *) * width * height);
	for (int i = 0; i < height; i++)
	{
		for (int j = 0; j < width; j++)
		{
			int r, g, b;
			fscanf(fp, "%d %d %d", &r, &g, &b);
			file->image[i * width + j] = malloc(sizeof(Color));
			Color *pixel = file->image[i * width + j];
			pixel->R = r;
			pixel->G = g;
			pixel->B = b;
			// file->image[i * width + j] = pixel;
		}
	}
	fclose(fp);
	// free(file)
	return file;
}

// Given an image, prints to stdout (e.g. with printf) a .ppm P3 file with the image's data.
void writeData(Image *image)
{
	printf("P3\n");
	printf("%d %d\n", image->cols, image->rows);
	printf("255\n");
	for (int i = 0; i < image->rows; i++)
	{
		for (int j = 0; j < image->cols; j++)
		{
			Color *pixel = image->image[i * image->cols + j];
			printf("%3d %3d %3d", pixel->R, pixel->G, pixel->B);
			if (j != image->cols - 1)
			{
				printf("   ");
			}
		}
		printf("\n");
	}
	// printf("\n");
}

// Frees an image
void freeImage(Image *image)
{
	for (int i = 0; i < image->cols * image->rows; i++)
	{
		free(image->image[i]);
	}
	free(image->image);
	free(image);
}